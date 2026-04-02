from tgbot.handlers.admin import admin_router
from tgbot.handlers.cancel import cancel_router
from tgbot.handlers.user import user_router
from tgbot.handlers.vpn_settings import vpn_router

routers_list = [
    admin_router,
    cancel_router,
    user_router,
    vpn_router
]

__all__ = [
    "routers_list",
]
