import json
from dataclasses import dataclass, field

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
class Certificates:
    fullchain_path: str
    key_path: str

    @staticmethod
    def from_env(env: Env):
        return Certificates(
            fullchain_path=env.str("CERT_FULLCHAIN_PATH", ""),
            key_path=env.str("CERT_KEY_PATH", ""),
        )

    def is_configured(self) -> bool:
        return bool(self.fullchain_path and self.key_path)


@dataclass
class XUI:
    @dataclass
    class Node:
        base_url: str
        username: str
        password: str
        inbound_id: int
        sub_base_url: str
        verify_ssl: bool

    @dataclass
    class StaticSubscription:
        url: str
        label: str = ""

    @dataclass
    class Plan:
        traffic_gb: int
        duration_days: int

        @property
        def traffic_bytes(self) -> int:
            return self.traffic_gb * 1024 * 1024 * 1024

    enabled: bool
    base_url: str
    username: str
    password: str
    inbound_id: int
    sub_base_url: str
    client_prefix: str
    verify_ssl: bool
    aggregator_base_url: str
    primary_label: str
    primary_host: str
    default_limit_ip: int
    default_plan: "XUI.Plan"
    gift_day_plan: "XUI.Plan"
    gift_week_plan: "XUI.Plan"
    gift_month_plan: "XUI.Plan"
    extra_static_sub_urls: list["XUI.StaticSubscription"]
    extra_nodes: list["XUI.Node"] = field(default_factory=list)

    def primary_node(self) -> "XUI.Node":
        return XUI.Node(
            base_url=self.base_url,
            username=self.username,
            password=self.password,
            inbound_id=self.inbound_id,
            sub_base_url=self.sub_base_url,
            verify_ssl=self.verify_ssl,
        )

    def all_nodes(self) -> list["XUI.Node"]:
        return [self.primary_node(), *self.extra_nodes]

    def has_extra_nodes(self) -> bool:
        return bool(self.extra_nodes)

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
        aggregator_base_url = env.str("XUI_AGGREGATOR_BASE_URL", "").rstrip("/")
        primary_label = env.str("XUI_PRIMARY_LABEL", "").strip()
        primary_host = env.str("XUI_PRIMARY_HOST", "").strip()
        default_limit_ip = env.int("XUI_DEFAULT_LIMIT_IP", 2)
        default_plan = XUI.Plan(
            traffic_gb=env.int("XUI_DEFAULT_TRAFFIC_GB", 60),
            duration_days=env.int("XUI_DEFAULT_DURATION_DAYS", 30),
        )
        gift_day_plan = XUI.Plan(
            traffic_gb=env.int("XUI_GIFT_1D_TRAFFIC_GB", 2),
            duration_days=env.int("XUI_GIFT_1D_DURATION_DAYS", 1),
        )
        gift_week_plan = XUI.Plan(
            traffic_gb=env.int("XUI_GIFT_7D_TRAFFIC_GB", 14),
            duration_days=env.int("XUI_GIFT_7D_DURATION_DAYS", 7),
        )
        gift_month_plan = XUI.Plan(
            traffic_gb=env.int("XUI_GIFT_30D_TRAFFIC_GB", 60),
            duration_days=env.int("XUI_GIFT_30D_DURATION_DAYS", 30),
        )
        extra_static_sub_urls_raw = env.str("XUI_EXTRA_STATIC_SUB_URLS", "[]").strip() or "[]"
        extra_static_sub_urls_payload = json.loads(extra_static_sub_urls_raw)
        if not isinstance(extra_static_sub_urls_payload, list):
            raise ValueError("XUI_EXTRA_STATIC_SUB_URLS must be a JSON array.")
        extra_static_sub_urls: list[XUI.StaticSubscription] = []
        for item in extra_static_sub_urls_payload:
            if isinstance(item, str):
                url = item.strip()
                if url:
                    extra_static_sub_urls.append(XUI.StaticSubscription(url=url))
                continue
            if isinstance(item, dict):
                url = str(item.get("url", "")).strip()
                label = str(item.get("label", "")).strip()
                if url:
                    extra_static_sub_urls.append(XUI.StaticSubscription(url=url, label=label))
                continue
            raise ValueError("Each XUI_EXTRA_STATIC_SUB_URLS item must be a string or object.")
        extra_nodes_raw = env.str("XUI_EXTRA_NODES", "[]").strip() or "[]"
        extra_nodes_payload = json.loads(extra_nodes_raw)
        if not isinstance(extra_nodes_payload, list):
            raise ValueError("XUI_EXTRA_NODES must be a JSON array.")
        extra_nodes: list[XUI.Node] = []
        for node in extra_nodes_payload:
            if not isinstance(node, dict):
                raise ValueError("Each XUI_EXTRA_NODES item must be an object.")
            extra_nodes.append(
                XUI.Node(
                    base_url=str(node.get("base_url", "")).rstrip("/"),
                    username=str(node.get("username", "")),
                    password=str(node.get("password", "")),
                    inbound_id=int(node.get("inbound_id", 0)),
                    sub_base_url=str(node.get("sub_base_url", "")),
                    verify_ssl=bool(node.get("verify_ssl", True)),
                )
            )
        return XUI(
            enabled=enabled,
            base_url=base_url,
            username=username,
            password=password,
            inbound_id=inbound_id,
            sub_base_url=sub_base_url,
            client_prefix=client_prefix,
            verify_ssl=verify_ssl,
            aggregator_base_url=aggregator_base_url,
            primary_label=primary_label,
            primary_host=primary_host,
            default_limit_ip=default_limit_ip,
            default_plan=default_plan,
            gift_day_plan=gift_day_plan,
            gift_week_plan=gift_week_plan,
            gift_month_plan=gift_month_plan,
            extra_static_sub_urls=extra_static_sub_urls,
            extra_nodes=extra_nodes,
        )


@dataclass
class Config:
    tg_bot: TgBot
    webhook: Webhook
    vpn_access: VpnAccess
    subscription: ChannelSubscription
    access_chat: AccessChat
    database: Database
    certificates: Certificates
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
        certificates=Certificates.from_env(env),
        xui=XUI.from_env(env),
    )
