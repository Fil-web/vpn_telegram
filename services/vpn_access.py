from urllib.parse import quote

from loader import config


def get_vpn_access_text() -> str:
    access_text = config.vpn_access.text.strip()
    if access_text:
        return access_text

    raise RuntimeError(
        "Не заполнен VPN_ACCESS_TEXT в .env. Добавьте туда ссылку, ключ или инструкцию для пользователя."
    )


def get_v2raytun_import_link(access_text: str) -> str | None:
    normalized = access_text.strip()
    if not normalized:
        return None

    supported_prefixes = ("vless://", "vmess://", "trojan://", "ss://")
    if not normalized.startswith(supported_prefixes):
        return None

    return f"v2raytun://import/{quote(normalized, safe='')}"
