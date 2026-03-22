from dataclasses import dataclass

from environs import Env


@dataclass
class TgBot:
    token: str
    admin_id: int
    port: int

    @staticmethod
    def from_env(env: Env):
        token = env.str("BOT_TOKEN")
        admin_id = env.int("ADMIN")
        port = env.int("BOT_PORT", 8080)

        return TgBot(token=token, admin_id=admin_id, port=port)


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
class VpnServer:
    base_url: str
    api_path: str
    api_token: str
    timeout: int

    @staticmethod
    def from_env(env: Env):
        base_url = env.str("VPN_API_BASE_URL")
        api_path = env.str("VPN_API_PATH", "/api/v1/telegram/vpn")
        api_token = env.str("VPN_API_TOKEN", "")
        timeout = env.int("VPN_API_TIMEOUT", 15)
        return VpnServer(
            base_url=base_url,
            api_path=api_path,
            api_token=api_token,
            timeout=timeout,
        )


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
    vpn_server: VpnServer
    subscription: ChannelSubscription


def load_config():
    from environs import Env
    env = Env()
    env.read_env('.env')
    return Config(
        tg_bot=TgBot.from_env(env),
        webhook=Webhook.from_env(env),
        vpn_server=VpnServer.from_env(env),
        subscription=ChannelSubscription.from_env(env),
    )
