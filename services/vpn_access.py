from urllib.parse import quote

from loader import config

IOS_APP_URL = "https://apps.apple.com/ru/app/v2ray-client/id6747379524"


def _public_base_url() -> str:
    scheme = "https" if config.certificates.is_configured() else "http"
    host = config.webhook.domain or config.tg_bot.ip
    return f"{scheme}://{host}:{config.tg_bot.port}"


def get_vpn_access_text() -> str:
    access_text = config.vpn_access.text.strip()
    if access_text:
        return access_text

    raise RuntimeError(
        "Не заполнен VPN_ACCESS_TEXT в .env. Добавьте туда ссылку, ключ или инструкцию для пользователя."
    )


def _is_supported_config(normalized: str) -> bool:
    supported_prefixes = (
        "vless://",
        "vmess://",
        "trojan://",
        "ss://",
        "https://",
        "http://",
    )
    return normalized.startswith(supported_prefixes)


def get_connect_page_link(access_text: str) -> str | None:
    normalized = access_text.strip()
    if not normalized:
        return None

    if not _is_supported_config(normalized):
        return None

    encoded = quote(normalized, safe="")
    return f"{_public_base_url()}/connect?config={encoded}"


def get_manual_page_link(access_text: str) -> str | None:
    normalized = access_text.strip()
    if not normalized:
        return None

    if not _is_supported_config(normalized):
        return None

    encoded = quote(normalized, safe="")
    return f"{_public_base_url()}/manual?config={encoded}"


def get_ios_app_link() -> str:
    return IOS_APP_URL
