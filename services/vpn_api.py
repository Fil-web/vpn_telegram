import json
import logging

from aiohttp import ClientError, ClientSession
from aiogram.types import User

from loader import config

logger = logging.getLogger(__name__)


def _build_request_url() -> str:
    base_url = config.vpn_server.base_url.rstrip("/")
    api_path = config.vpn_server.api_path.lstrip("/")
    return f"{base_url}/{api_path}"


def _extract_access_payload(payload: dict) -> str:
    if isinstance(payload.get("links"), list):
        return "\n\n".join(str(item) for item in payload["links"] if item)

    for key in ("vpn_key", "access_url", "subscription_url", "message", "text"):
        value = payload.get(key)
        if value:
            return str(value)

    if isinstance(payload.get("data"), dict):
        nested = _extract_access_payload(payload["data"])
        if nested:
            return nested

    return json.dumps(payload, ensure_ascii=False, indent=2)


async def fetch_vpn_access(user: User) -> str:
    headers = {"Content-Type": "application/json"}
    if config.vpn_server.api_token:
        headers["Authorization"] = f"Bearer {config.vpn_server.api_token}"

    payload = {
        "telegram_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
    }

    request_url = _build_request_url()
    timeout = config.vpn_server.timeout

    try:
        async with ClientSession(headers=headers) as session:
            async with session.post(request_url, json=payload, timeout=timeout) as response:
                response_text = await response.text()
                if response.status >= 400:
                    logger.error("VPN API error %s: %s", response.status, response_text)
                    raise RuntimeError(
                        f"Сервер вернул ошибку {response.status}. "
                        "Проверьте путь API, авторизацию и формат запроса."
                    )

                try:
                    response_payload = json.loads(response_text)
                except json.JSONDecodeError:
                    return response_text.strip()

                return _extract_access_payload(response_payload)
    except ClientError as exc:
        logger.exception("VPN API request failed")
        raise RuntimeError(
            "Не удалось связаться с сервером VPN. Проверьте адрес сервера и доступность API."
        ) from exc
