from urllib.parse import quote

from loader import config


def get_vpn_access_text() -> str:
    access_text = config.vpn_access.text.strip()
    if access_text:
        return access_text

    raise RuntimeError(
        "Не заполнен VPN_ACCESS_TEXT в .env. Добавьте туда ссылку, ключ или инструкцию для пользователя."
    )


def _is_supported_config(normalized: str) -> bool:
    supported_prefixes = ("vless://", "vmess://", "trojan://", "ss://")
    return normalized.startswith(supported_prefixes)


def get_connect_page_link(access_text: str) -> str | None:
    normalized = access_text.strip()
    if not normalized:
        return None

    if not _is_supported_config(normalized):
        return None

    encoded = quote(normalized, safe="")
    return f"http://{config.tg_bot.ip}:{config.tg_bot.port}/connect?config={encoded}"


def get_manual_page_link(access_text: str) -> str | None:
    normalized = access_text.strip()
    if not normalized:
        return None

    if not _is_supported_config(normalized):
        return None

    encoded = quote(normalized, safe="")
    return f"http://{config.tg_bot.ip}:{config.tg_bot.port}/manual?config={encoded}"
