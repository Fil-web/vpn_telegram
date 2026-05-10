import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder

from loader import config
from services.user_store import StoredUser

logger = logging.getLogger(__name__)


def keyboard_start():
    builder = InlineKeyboardBuilder()
    builder.button(text='🚀 Подключить VPN', callback_data='vpn')
    builder.button(text='ℹ️ Как это работает', callback_data='help')
    builder.adjust(2)
    return builder.as_markup()


def keyboard_subscription():
    builder = InlineKeyboardBuilder()
    if config.subscription.channel_url:
        builder.button(text='📢 Подписаться на канал', url=config.subscription.channel_url)
    builder.button(text='✅ Проверить подписку', callback_data='check_subscription')
    builder.button(text='📡 Получить VPN', callback_data='vpn')
    builder.adjust(1)
    return builder.as_markup()


def keyboard_vpn_access(
    android_connect_link: str | None = None,
    ios_app_link: str | None = None,
    manual_link: str | None = None,
):
    builder = InlineKeyboardBuilder()
    if android_connect_link:
        builder.button(text='🤖 Android: Подключить в v2RayTun', url=android_connect_link)
    if ios_app_link:
        builder.button(text='🍎 iPhone / iOS: Открыть приложение', url=ios_app_link)
    if manual_link:
        builder.button(text='🛠 Добавить VPN вручную', url=manual_link)
    builder.adjust(1)
    return builder.as_markup()


def keyboard_help():
    builder = InlineKeyboardBuilder()
    if config.subscription.channel_url:
        builder.button(text='📢 Наш канал', url=config.subscription.channel_url)
    return builder.as_markup()


def keyboard_cancel():
    builder = InlineKeyboardBuilder()
    builder.button(text='❌Выйти из меню', callback_data='cancel')
    return builder.as_markup()


def keyboard_admin():
    builder = InlineKeyboardBuilder()
    builder.button(text='📊 Сводка', callback_data='admin_menu')
    builder.button(text='👥 Пользователи', callback_data='admin_users')
    builder.button(text='🚫 Баны', callback_data='admin_banned')
    builder.button(text='ℹ️ Команды', callback_data='admin_help')
    builder.adjust(2, 2)
    return builder.as_markup()


def keyboard_admin_users(users: list[StoredUser]):
    builder = InlineKeyboardBuilder()
    builder.button(text='📊 Сводка', callback_data='admin_menu')
    builder.button(text='ℹ️ Команды', callback_data='admin_help')
    for user in users:
        builder.button(
            text=user.display_name[:32],
            callback_data=f'admin_user:{user.telegram_id}',
        )
    builder.adjust(2, *([1] * len(users)))
    return builder.as_markup()


def keyboard_admin_user_actions(user_id: int, is_banned: bool = False):
    builder = InlineKeyboardBuilder()
    builder.button(text='🎁 1 день', callback_data=f'admin_gift:1:{user_id}')
    builder.button(text='🎁 7 дней', callback_data=f'admin_gift:7:{user_id}')
    builder.button(text='🎁 30 дней', callback_data=f'admin_gift:30:{user_id}')
    if is_banned:
        builder.button(text='✅ Разбанить', callback_data=f'admin_unban:{user_id}')
    else:
        builder.button(text='🚫 Забанить', callback_data=f'admin_ban:{user_id}')
    builder.button(text='◀️ К списку', callback_data='admin_users')
    builder.button(text='📊 Сводка', callback_data='admin_menu')
    builder.adjust(2, 2, 2)
    return builder.as_markup()
