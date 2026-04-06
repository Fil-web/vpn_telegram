import json
import secrets
import uuid
from dataclasses import dataclass

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
        return bool(
            config.xui.enabled
            and self.base_url
            and config.xui.username
            and config.xui.password
            and config.xui.inbound_id
            and config.xui.sub_base_url
        )

    def _client_email(self, user: User) -> str:
        return f"{config.xui.client_prefix}_{user.id}"

    def _subscription_url(self, sub_id: str) -> str:
        return f"{config.xui.sub_base_url.rstrip('/')}/{sub_id}"

    async def _login(self, session: ClientSession) -> None:
        response = await session.post(
            f"{self.base_url}/login",
            data={
                "username": config.xui.username,
                "password": config.xui.password,
            },
            ssl=self.verify_ssl,
        )
        response.raise_for_status()

    async def _get_inbounds(self, session: ClientSession) -> list[dict]:
        response = await session.get(
            f"{self.base_url}/panel/api/inbounds/list",
            ssl=self.verify_ssl,
        )
        response.raise_for_status()
        payload = await response.json()
        if not payload.get("success"):
            raise RuntimeError(payload.get("msg", "Failed to load x-ui inbounds."))
        return payload.get("obj") or []

    async def _get_target_inbound(self, session: ClientSession) -> dict:
        inbounds = await self._get_inbounds(session)
        for inbound in inbounds:
            if int(inbound.get("id", 0)) == config.xui.inbound_id:
                return inbound
        raise RuntimeError(f"x-ui inbound {config.xui.inbound_id} not found.")

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

    async def get_or_create_access(self, user: User) -> str:
        if not self.is_enabled():
            raise RuntimeError("x-ui personal issuance is disabled.")

        email = self._client_email(user)
        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as session:
            await self._login(session)
            inbound = await self._get_target_inbound(session)
            existing_client = self._extract_client(inbound, email)
            if existing_client:
                user_store.set_xui_mapping(
                    user.id,
                    email=existing_client.email,
                    client_id=existing_client.client_id,
                    sub_id=existing_client.sub_id,
                    inbound_id=existing_client.inbound_id,
                )
                return self._subscription_url(existing_client.sub_id)

            client_id = str(uuid.uuid4())
            sub_id = secrets.token_urlsafe(12).lower().replace("-", "")[:16]
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
                f"{self.base_url}/panel/api/inbounds/addClient",
                data={
                    "id": str(config.xui.inbound_id),
                    "settings": json.dumps({"clients": [client_payload]}, ensure_ascii=False),
                },
                ssl=self.verify_ssl,
            )
            response.raise_for_status()
            payload = await response.json()
            if not payload.get("success"):
                raise RuntimeError(payload.get("msg", "Failed to create x-ui client."))

        user_store.set_xui_mapping(
            user.id,
            email=email,
            client_id=client_id,
            sub_id=sub_id,
            inbound_id=config.xui.inbound_id,
        )
        return self._subscription_url(sub_id)

    async def disable_user(self, stored_user: StoredUser) -> None:
        if not self.is_enabled():
            return
        if not stored_user.xui_client_id or not stored_user.xui_inbound_id:
            return

        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as session:
            await self._login(session)
            response = await session.post(
                f"{self.base_url}/panel/api/inbounds/{stored_user.xui_inbound_id}/delClient/{stored_user.xui_client_id}",
                ssl=self.verify_ssl,
            )
            response.raise_for_status()


xui_service = XUIService()
