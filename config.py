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
class Config:
    tg_bot: TgBot
    webhook: Webhook
    vpn_access: VpnAccess
    subscription: ChannelSubscription


def load_config():
    from environs import Env
    env = Env()
    env.read_env('.env')
    return Config(
        tg_bot=TgBot.from_env(env),
        webhook=Webhook.from_env(env),
        vpn_access=VpnAccess.from_env(env),
        subscription=ChannelSubscription.from_env(env),
    )
