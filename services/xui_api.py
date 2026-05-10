import base64
import json
import secrets
import ssl
import uuid
from dataclasses import dataclass
from urllib.parse import quote, urlsplit, urlunsplit

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

    async def _login(self, session: ClientSession, node: config.xui.Node) -> None:
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

    def _extract_client(self, inbound: dict, email: str) -> XUIClientRecord | None:
        settings = inbound.get("settings")
        if isinstance(settings, str):
            settings = json.loads(settings)
        clients = settings.get("clients", []) if isinstance(settings, dict) else []
        for client in clients:
            if client.get("email") == email:
                return XUIClientRecord(
                    email=client.get("email"),
                    client_id=client.get("id"),
                    sub_id=client.get("subId"),
                    inbound_id=int(inbound.get("id", 0)),
                    enabled=bool(client.get("enable", True)),
                )
        return None

    async def _create_client(
        self,
        session: ClientSession,
        node: config.xui.Node,
        user: User,
        email: str,
        sub_id: str,
    ) -> str:
        client_id = str(uuid.uuid4())
        client_payload = {
            "id": client_id,
            "flow": "",
            "email": email,
            "limitIp": 2,
            "totalGB": 0,
            "expiryTime": 0,
            "enable": True,
            "tgId": str(user.id),
            "subId": sub_id,
            "comment": user.username or user.first_name or "",
            "reset": 0,
        }
        response = await session.post(
            f"{node.base_url}/panel/api/inbounds/addClient",
            data={
                "id": str(node.inbound_id),
                "settings": json.dumps({"clients": [client_payload]}, ensure_ascii=False),
            },
            ssl=node.verify_ssl,
        )
        response.raise_for_status()
        payload = await response.json()
        if not payload.get("success"):
            raise RuntimeError(payload.get("msg", f"Failed to create x-ui client at {node.base_url}."))
        return client_id

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

        client_id = await self._create_client(session, node, user, email, sub_id)
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
                client_id = await self._create_client(session, primary_node, user, email, sub_id)
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
                    ssl=node.verify_ssl,
                )
                response.raise_for_status()

    async def build_subscription_payload(self, sub_id: str) -> str:
        if not self.is_enabled():
            raise RuntimeError("x-ui personal issuance is disabled.")

        all_lines: list[str] = []
        seen: set[str] = set()
        async with ClientSession() as session:
            for index, node in enumerate(config.xui.all_nodes()):
                url = self._subscription_url(node, sub_id)
                response = await session.get(url, ssl=node.verify_ssl)
                response.raise_for_status()
                payload = await response.text()
                for line in self._normalize_subscription_lines(payload):
                    if index == 0:
                        line = self._apply_label(line, config.xui.primary_label)
                    if line not in seen:
                        seen.add(line)
                        all_lines.append(line)
            for item in config.xui.extra_static_sub_urls:
                response = await session.get(item.url)
                response.raise_for_status()
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
