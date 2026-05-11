import base64
import json
import uuid
from decimal import Decimal

from aiohttp import ClientSession

from loader import config
from services.user_store import StoredUser, user_store


class YooKassaService:
    api_base = "https://api.yookassa.ru/v3"

    def is_enabled(self) -> bool:
        return config.yookassa.enabled

    def is_configured(self) -> bool:
        return config.yookassa.is_configured()

    def _auth_header(self) -> str:
        token = f"{config.yookassa.shop_id}:{config.yookassa.secret_key}".encode("utf-8")
        return "Basic " + base64.b64encode(token).decode("ascii")

    def _return_url(self) -> str:
        scheme = "https" if config.certificates.is_configured() else "http"
        host = config.webhook.domain or config.tg_bot.ip
        return f"{scheme}://{host}:{config.tg_bot.port}{config.yookassa.return_path}"

    async def create_payment(self, stored_user: StoredUser) -> dict:
        if not self.is_configured():
            raise RuntimeError("Оплата временно недоступна. Попробуйте чуть позже или напишите администратору.")

        amount = Decimal(config.access_policy.price_rub).quantize(Decimal("1.00"))
        payload = {
            "amount": {
                "value": str(amount),
                "currency": "RUB",
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": self._return_url(),
            },
            "description": f"VPN на {config.access_policy.paid_duration_days} дней для {stored_user.telegram_id}",
            "metadata": {
                "telegram_id": str(stored_user.telegram_id),
                "plan": "monthly_vpn",
            },
        }
        headers = {
            "Authorization": self._auth_header(),
            "Idempotence-Key": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }
        async with ClientSession() as session:
            response = await session.post(
                f"{self.api_base}/payments",
                headers=headers,
                data=json.dumps(payload),
            )
            response.raise_for_status()
            body = await response.json()
        user_store.set_payment_state(
            stored_user.telegram_id,
            payment_id=body["id"],
            payment_status=body["status"],
        )
        return body

    async def get_payment(self, payment_id: str) -> dict:
        headers = {
            "Authorization": self._auth_header(),
        }
        async with ClientSession() as session:
            response = await session.get(
                f"{self.api_base}/payments/{payment_id}",
                headers=headers,
            )
            response.raise_for_status()
            return await response.json()

    def resolve_user_from_notification(self, payload: dict) -> StoredUser | None:
        payment_object = payload.get("object") or {}
        metadata = payment_object.get("metadata") or {}
        telegram_id = metadata.get("telegram_id")
        if telegram_id and str(telegram_id).isdigit():
            return user_store.get_user(int(telegram_id))
        payment_id = payment_object.get("id")
        if payment_id:
            return user_store.get_user_by_payment_id(payment_id)
        return None


yookassa_service = YooKassaService()
