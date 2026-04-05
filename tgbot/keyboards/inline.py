import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder

from loader import config

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
    android_manual_link: str | None = None,
    ios_manual_link: str | None = None,
):
    builder = InlineKeyboardBuilder()
    if android_connect_link:
        builder.button(text='🤖 Android: Подключить в v2RayTun', url=android_connect_link)
    if ios_app_link:
        builder.button(text='🍎 iPhone / iOS: Открыть приложение', url=ios_app_link)
    if android_manual_link:
        builder.button(text='🛠 Android: Добавить вручную', url=android_manual_link)
    if ios_manual_link:
        builder.button(text='🛠 iPhone / iOS: Добавить вручную', url=ios_manual_link)
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
