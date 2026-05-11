import base64
import json
import secrets
import ssl
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from aiohttp import ClientSession, CookieJar
from aiogram.types import User

from loader import config
from services.user_store import StoredUser, user_store


@dataclass
class XUIClientRecord:
    email: str
    client_id: str
    sub_id: str
    inbound_id: int
    enabled: bool


@dataclass
class XUIGrantResult:
    email: str
    duration_days: int
    traffic_gb: int
    expires_at: datetime


class XUIService:
    def __init__(self):
        self.base_url = config.xui.base_url.rstrip("/")
        self.verify_ssl = config.xui.verify_ssl

    def is_enabled(self) -> bool:
        nodes = config.xui.all_nodes()
        return bool(
            config.xui.enabled
            and nodes
            and all(
                node.base_url
                and node.username
                and node.password
                and node.inbound_id
                and node.sub_base_url
                for node in nodes
            )
        )

    def _client_email(self, user: User) -> str:
        return f"{config.xui.client_prefix}_{user.id}"

    def _subscription_url(self, node: config.xui.Node, sub_id: str) -> str:
        return f"{node.sub_base_url.rstrip('/')}/{sub_id}"

    def _public_subscription_url(self, sub_id: str) -> str:
        if config.xui.has_extra_nodes() or config.xui.extra_static_sub_urls:
            base_url = config.xui.aggregator_base_url.rstrip("/")
            if not base_url:
                scheme = "https" if config.certificates.is_configured() else "http"
                host = config.webhook.domain or config.tg_bot.ip
                base_url = f"{scheme}://{host}:{config.tg_bot.port}"
            return f"{base_url}/sub/{sub_id}"
        return self._subscription_url(config.xui.primary_node(), sub_id)

    def _browser_headers(self, node: config.xui.Node) -> dict[str, str]:
        parsed = urlsplit(node.base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        referer = node.base_url.rstrip("/") + "/"
        return {
            "Origin": origin,
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0",
        }

    async def _csrf_headers(self, session: ClientSession, node: config.xui.Node) -> dict[str, str]:
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0",
        }
        csrf_token = await self._get_csrf_token(session, node)
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token
        return headers

    async def _get_csrf_token(self, session: ClientSession, node: config.xui.Node) -> str | None:
        response = await session.get(
            f"{node.base_url}/csrf-token",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Mozilla/5.0",
            },
            ssl=node.verify_ssl,
        )
        if response.status == 404:
            await response.release()
            return None
        response.raise_for_status()
        payload = await response.json()
        token = payload.get("obj")
        return token if isinstance(token, str) and token else None

    async def _login(self, session: ClientSession, node: config.xui.Node) -> None:
        csrf_token = await self._get_csrf_token(session, node)
        if not csrf_token:
            warmup_response = await session.get(
                node.base_url,
                headers=self._browser_headers(node),
                ssl=node.verify_ssl,
            )
            warmup_response.raise_for_status()
            response = await session.post(
                f"{node.base_url}/login",
                data={
                    "username": node.username,
                    "password": node.password,
                },
                headers=self._browser_headers(node),
                ssl=node.verify_ssl,
            )
            response.raise_for_status()
            return
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0",
        }
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token
        response = await session.post(
            f"{node.base_url}/login",
            data={
                "username": node.username,
                "password": node.password,
            },
            headers=headers,
            ssl=node.verify_ssl,
        )
        response.raise_for_status()

    async def _get_inbounds(self, session: ClientSession, node: config.xui.Node) -> list[dict]:
        response = await session.get(
            f"{node.base_url}/panel/api/inbounds/list",
            ssl=node.verify_ssl,
        )
        response.raise_for_status()
        payload = await response.json()
        if not payload.get("success"):
            raise RuntimeError(payload.get("msg", "Failed to load x-ui inbounds."))
        return payload.get("obj") or []

    async def _get_target_inbound(self, session: ClientSession, node: config.xui.Node) -> dict:
        inbounds = await self._get_inbounds(session, node)
        for inbound in inbounds:
            if int(inbound.get("id", 0)) == node.inbound_id:
                return inbound
        raise RuntimeError(f"x-ui inbound {node.inbound_id} not found at {node.base_url}.")

    def _client_dicts(self, inbound: dict) -> list[dict]:
        settings = inbound.get("settings")
        if isinstance(settings, str):
            settings = json.loads(settings)
        if not isinstance(settings, dict):
            return []
        clients = settings.get("clients", [])
        return clients if isinstance(clients, list) else []

    def _extract_client(self, inbound: dict, email: str) -> XUIClientRecord | None:
        for client in self._client_dicts(inbound):
            if client.get("email") == email:
                return XUIClientRecord(
                    email=client.get("email"),
                    client_id=client.get("id"),
                    sub_id=client.get("subId"),
                    inbound_id=int(inbound.get("id", 0)),
                    enabled=bool(client.get("enable", True)),
                )
        return None

    def _find_client_payload(self, inbound: dict, email: str) -> dict | None:
        for client in self._client_dicts(inbound):
            if client.get("email") == email:
                return client
        return None

    def _future_expiry_ms(self, duration_days: int) -> tuple[int, datetime]:
        expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
        return int(expires_at.timestamp() * 1000), expires_at

    def _build_client_payload(
        self,
        *,
        user: User | None,
        email: str,
        client_id: str,
        sub_id: str,
        traffic_gb: int,
        duration_days: int,
        existing: dict | None = None,
    ) -> tuple[dict, datetime]:
        expiry_ms, expires_at = self._future_expiry_ms(duration_days)
        payload = dict(existing or {})
        payload.update(
            {
                "id": client_id,
                "flow": payload.get("flow", ""),
                "email": email,
                "limitIp": int(payload.get("limitIp", config.xui.default_limit_ip) or config.xui.default_limit_ip),
                "totalGB": traffic_gb * 1024 * 1024 * 1024,
                "expiryTime": expiry_ms,
                "enable": True,
                "tgId": str(user.id) if user else str(payload.get("tgId", "")),
                "subId": sub_id,
                "comment": (
                    user.username or user.first_name or ""
                    if user
                    else str(payload.get("comment", ""))
                ),
                "reset": int(payload.get("reset", 0) or 0),
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
        )
        if user and "created_at" not in payload:
            payload["created_at"] = payload["updated_at"]
        return payload, expires_at

    async def _create_client(
        self,
        session: ClientSession,
        node: config.xui.Node,
        user: User,
        email: str,
        sub_id: str,
    ) -> tuple[str, datetime]:
        client_id = str(uuid.uuid4())
        client_payload, expires_at = self._build_client_payload(
            user=user,
            email=email,
            client_id=client_id,
            sub_id=sub_id,
            traffic_gb=config.xui.default_plan.traffic_gb,
            duration_days=config.xui.default_plan.duration_days,
        )
        response = await session.post(
            f"{node.base_url}/panel/api/inbounds/addClient",
            data={
                "id": str(node.inbound_id),
                "settings": json.dumps({"clients": [client_payload]}, ensure_ascii=False),
            },
            headers=await self._csrf_headers(session, node),
            ssl=node.verify_ssl,
        )
        response.raise_for_status()
        payload = await response.json()
        if not payload.get("success"):
            raise RuntimeError(payload.get("msg", f"Failed to create x-ui client at {node.base_url}."))
        return client_id, expires_at

    async def _update_client(
        self,
        session: ClientSession,
        node: config.xui.Node,
        inbound_id: int,
        client_id: str,
        payload: dict,
    ) -> None:
        response = await session.post(
            f"{node.base_url}/panel/api/inbounds/updateClient/{client_id}",
            data={
                "id": str(inbound_id),
                "settings": json.dumps({"clients": [payload]}, ensure_ascii=False),
            },
            headers=await self._csrf_headers(session, node),
            ssl=node.verify_ssl,
        )
        response.raise_for_status()
        body = await response.json()
        if not body.get("success"):
            raise RuntimeError(body.get("msg", f"Failed to update x-ui client at {node.base_url}."))

    async def _reset_client_traffic(
        self,
        session: ClientSession,
        node: config.xui.Node,
        inbound_id: int,
        email: str,
    ) -> None:
        response = await session.post(
            f"{node.base_url}/panel/api/inbounds/{inbound_id}/resetClientTraffic/{email}",
            headers=await self._csrf_headers(session, node),
            ssl=node.verify_ssl,
        )
        response.raise_for_status()

    async def _ensure_client_on_node(
        self,
        session: ClientSession,
        node: config.xui.Node,
        user: User,
        email: str,
        sub_id: str,
    ) -> XUIClientRecord:
        await self._login(session, node)
        inbound = await self._get_target_inbound(session, node)
        existing_client = self._extract_client(inbound, email)
        if existing_client:
            return existing_client

        client_id, _ = await self._create_client(session, node, user, email, sub_id)
        return XUIClientRecord(
            email=email,
            client_id=client_id,
            sub_id=sub_id,
            inbound_id=node.inbound_id,
            enabled=True,
        )

    def _normalize_subscription_lines(self, payload: str) -> list[str]:
        normalized = payload.strip()
        if not normalized:
            return []
        if "://" in normalized:
            return [line.strip() for line in normalized.splitlines() if line.strip()]

        compact = "".join(normalized.split())
        padding = "=" * (-len(compact) % 4)
        try:
            decoded = base64.b64decode(compact + padding).decode("utf-8")
        except Exception:
            return [line.strip() for line in normalized.splitlines() if line.strip()]
        return [line.strip() for line in decoded.splitlines() if line.strip()]

    def _apply_label(self, line: str, label: str) -> str:
        if not label or "://" not in line or "#" not in line:
            return line
        parts = urlsplit(line)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, quote(label)))

    def _apply_host(self, line: str, host: str) -> str:
        if not host or "://" not in line:
            return line
        parts = urlsplit(line)
        if "@" not in parts.netloc:
            return line
        userinfo, _, endpoint = parts.netloc.rpartition("@")
        _, sep, port = endpoint.partition(":")
        new_endpoint = host if not sep else f"{host}:{port}"
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        query = urlencode(query_pairs, doseq=True)
        return urlunsplit((parts.scheme, f"{userinfo}@{new_endpoint}", parts.path, query, parts.fragment))

    def _user_from_stored(self, stored_user: StoredUser) -> User:
        return User(
            id=stored_user.telegram_id,
            is_bot=False,
            first_name=stored_user.first_name or "",
            last_name=stored_user.last_name,
            username=stored_user.username,
            language_code=stored_user.language_code,
        )

    async def get_or_create_access(self, user: User) -> str:
        if not self.is_enabled():
            raise RuntimeError("x-ui personal issuance is disabled.")

        email = self._client_email(user)
        nodes = config.xui.all_nodes()
        primary_node = nodes[0]
        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as session:
            await self._login(session, primary_node)
            inbound = await self._get_target_inbound(session, primary_node)
            existing_primary = self._extract_client(inbound, email)
            sub_id = existing_primary.sub_id if existing_primary else secrets.token_urlsafe(12).lower().replace("-", "")[:16]
            if existing_primary:
                primary_record = existing_primary
            else:
                client_id, _ = await self._create_client(session, primary_node, user, email, sub_id)
                primary_record = XUIClientRecord(
                    email=email,
                    client_id=client_id,
                    sub_id=sub_id,
                    inbound_id=primary_node.inbound_id,
                    enabled=True,
                )

        for node in nodes[1:]:
            async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as session:
                await self._ensure_client_on_node(session, node, user, email, sub_id)

        user_store.set_xui_mapping(
            user.id,
            email=primary_record.email,
            client_id=primary_record.client_id,
            sub_id=primary_record.sub_id,
            inbound_id=primary_record.inbound_id,
        )
        return self._public_subscription_url(sub_id)

    async def grant_plan(self, stored_user: StoredUser, plan: config.xui.Plan) -> XUIGrantResult:
        if not self.is_enabled():
            raise RuntimeError("x-ui personal issuance is disabled.")
        if not stored_user.xui_email:
            raise RuntimeError("У пользователя еще нет выданного VPN-профиля.")

        email = stored_user.xui_email
        expires_at: datetime | None = None

        for node in config.xui.all_nodes():
            async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as session:
                await self._login(session, node)
                inbound = await self._get_target_inbound(session, node)
                existing_client = self._extract_client(inbound, email)
                if not existing_client:
                    continue
                existing_payload = self._find_client_payload(inbound, email)
                updated_payload, node_expires_at = self._build_client_payload(
                    user=None,
                    email=email,
                    client_id=existing_client.client_id,
                    sub_id=existing_client.sub_id,
                    traffic_gb=plan.traffic_gb,
                    duration_days=plan.duration_days,
                    existing=existing_payload,
                )
                await self._update_client(
                    session,
                    node,
                    existing_client.inbound_id,
                    existing_client.client_id,
                    updated_payload,
                )
                await self._reset_client_traffic(session, node, existing_client.inbound_id, email)
                expires_at = node_expires_at

        if not expires_at:
            raise RuntimeError("Не удалось найти VPN-профиль пользователя в x-ui.")

        return XUIGrantResult(
            email=email,
            duration_days=plan.duration_days,
            traffic_gb=plan.traffic_gb,
            expires_at=expires_at,
        )

    async def disable_user(self, stored_user: StoredUser) -> None:
        if not self.is_enabled():
            return
        if not stored_user.xui_email:
            return

        for node in config.xui.all_nodes():
            async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as session:
                await self._login(session, node)
                inbound = await self._get_target_inbound(session, node)
                existing_client = self._extract_client(inbound, stored_user.xui_email)
                if not existing_client:
                    continue
                response = await session.post(
                    f"{node.base_url}/panel/api/inbounds/{existing_client.inbound_id}/delClient/{existing_client.client_id}",
                    headers=await self._csrf_headers(session, node),
                    ssl=node.verify_ssl,
                )
                response.raise_for_status()

    async def build_subscription_payload(self, sub_id: str) -> str:
        if not self.is_enabled():
            raise RuntimeError("x-ui personal issuance is disabled.")

        all_lines: list[str] = []
        seen: set[str] = set()
        stored_user = user_store.get_user_by_sub_id(sub_id)
        async with ClientSession() as session:
            for index, node in enumerate(config.xui.all_nodes()):
                url = self._subscription_url(node, sub_id)
                response = await session.get(url, ssl=node.verify_ssl)
                if response.status >= 400 and stored_user and stored_user.xui_email:
                    await response.release()
                    async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as node_session:
                        await self._ensure_client_on_node(
                            node_session,
                            node,
                            self._user_from_stored(stored_user),
                            stored_user.xui_email,
                            sub_id,
                        )
                    response = await session.get(url, ssl=node.verify_ssl)
                if response.status >= 400:
                    if index == 0:
                        response.raise_for_status()
                    await response.release()
                    continue
                payload = await response.text()
                for line in self._normalize_subscription_lines(payload):
                    if index == 0:
                        line = self._apply_host(line, config.xui.primary_host)
                    line = self._apply_label(line, node.label)
                    if line not in seen:
                        seen.add(line)
                        all_lines.append(line)
            for item in config.xui.extra_static_sub_urls:
                response = await session.get(item.url)
                if response.status >= 400:
                    await response.release()
                    continue
                payload = await response.text()
                for line in self._normalize_subscription_lines(payload):
                    line = self._apply_label(line, item.label)
                    if line not in seen:
                        seen.add(line)
                        all_lines.append(line)

        if not all_lines:
            raise RuntimeError("Subscription payload is empty.")

        combined = "\n".join(all_lines).encode("utf-8")
        return base64.b64encode(combined).decode("ascii")


xui_service = XUIService()
