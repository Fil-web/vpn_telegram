from loader import config


def get_vpn_access_text() -> str:
    access_text = config.vpn_access.text.strip()
    if access_text:
        return access_text

    raise RuntimeError(
        "Не заполнен VPN_ACCESS_TEXT в .env. Добавьте туда ссылку, ключ или инструкцию для пользователя."
    )
