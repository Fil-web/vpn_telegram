from dataclasses import dataclass

from environs import Env


@dataclass
class TgBot:
    token: str
    admin_id: int
    ip: str
    port: int

    @staticmethod
    def from_env(env: Env):
        token = env.str("BOT_TOKEN")
        admin_id = env.int("ADMIN")
        ip = env.str("BOT_IP", "127.0.0.1")
        port = env.int("BOT_PORT", 8080)

        return TgBot(token=token, admin_id=admin_id, ip=ip, port=port)


@dataclass
class Webhook:
    url: str
    domain: str
    use_webhook: bool

    @staticmethod
    def from_env(env: Env):
        url = env.str('SERVER_URL')
        domain = env.str('DOMAIN')
        use_webhook = env.bool('USE_WEBHOOK')
        return Webhook(url=url, domain=domain, use_webhook=use_webhook)


@dataclass
class VpnAccess:
    text: str

    @staticmethod
    def from_env(env: Env):
        text = env.str("VPN_ACCESS_TEXT", "")
        return VpnAccess(text=text)


@dataclass
class ChannelSubscription:
    channel_id: str
    channel_url: str
    required: bool

    @staticmethod
    def from_env(env: Env):
        channel_id = env.str("CHANNEL_ID")
        channel_url = env.str("CHANNEL_URL", "")
        required = env.bool("REQUIRE_CHANNEL_SUBSCRIPTION", True)
        return ChannelSubscription(
            channel_id=channel_id,
            channel_url=channel_url,
            required=required,
        )


@dataclass
class AccessChat:
    chat_id: str
    chat_url: str
    required: bool

    @staticmethod
    def from_env(env: Env):
        chat_id = env.str("ACCESS_CHAT_ID", "")
        chat_url = env.str("ACCESS_CHAT_URL", "")
        required = env.bool("REQUIRE_CHAT_MEMBERSHIP", False)
        return AccessChat(
            chat_id=chat_id,
            chat_url=chat_url,
            required=required,
        )


@dataclass
class Database:
    path: str

    @staticmethod
    def from_env(env: Env):
        path = env.str("DATABASE_PATH", "bot.db")
        return Database(path=path)


@dataclass
class XUI:
    enabled: bool
    base_url: str
    username: str
    password: str
    inbound_id: int
    sub_base_url: str
    client_prefix: str
    verify_ssl: bool

    @staticmethod
    def from_env(env: Env):
        enabled = env.bool("XUI_ENABLED", False)
        base_url = env.str("XUI_BASE_URL", "")
        username = env.str("XUI_USERNAME", "")
        password = env.str("XUI_PASSWORD", "")
        inbound_id = env.int("XUI_INBOUND_ID", 0)
        sub_base_url = env.str("XUI_SUB_BASE_URL", "")
        client_prefix = env.str("XUI_CLIENT_PREFIX", "tg")
        verify_ssl = env.bool("XUI_VERIFY_SSL", True)
        return XUI(
            enabled=enabled,
            base_url=base_url,
            username=username,
            password=password,
            inbound_id=inbound_id,
            sub_base_url=sub_base_url,
            client_prefix=client_prefix,
            verify_ssl=verify_ssl,
        )


@dataclass
class Config:
    tg_bot: TgBot
    webhook: Webhook
    vpn_access: VpnAccess
    subscription: ChannelSubscription
    access_chat: AccessChat
    database: Database
    xui: XUI


def load_config():
    from environs import Env
    env = Env()
    env.read_env('.env')
    return Config(
        tg_bot=TgBot.from_env(env),
        webhook=Webhook.from_env(env),
        vpn_access=VpnAccess.from_env(env),
        subscription=ChannelSubscription.from_env(env),
        access_chat=AccessChat.from_env(env),
        database=Database.from_env(env),
        xui=XUI.from_env(env),
    )
