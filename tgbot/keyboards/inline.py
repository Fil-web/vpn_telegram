import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder

from loader import config

logger = logging.getLogger(__name__)


def keyboard_start():
    builder = InlineKeyboardBuilder()
    builder.button(text='Доступ к VPN', callback_data='vpn')
    builder.button(text='Что за VPN?', callback_data='help')
    builder.adjust(2)
    return builder.as_markup()


def keyboard_subscription():
    builder = InlineKeyboardBuilder()
    if config.subscription.channel_url:
        builder.button(text='Подписаться на канал', url=config.subscription.channel_url)
    builder.button(text='Проверить подписку', callback_data='check_subscription')
    builder.button(text='Получить доступ', callback_data='vpn')
    builder.adjust(1)
    return builder.as_markup()


def keyboard_vpn_access(connect_page_link: str | None = None):
    builder = InlineKeyboardBuilder()
    if connect_page_link:
        builder.button(text='Подключить в v2RayTun', url=connect_page_link)
    if config.subscription.channel_url:
        builder.button(text='Наш канал', url=config.subscription.channel_url)
    builder.adjust(1)
    return builder.as_markup()


def keyboard_help():
    builder = InlineKeyboardBuilder()
    if config.subscription.channel_url:
        builder.button(text='Наш канал', url=config.subscription.channel_url)
    return builder.as_markup()


def keyboard_cancel():
    builder = InlineKeyboardBuilder()
    builder.button(text='❌Выйти из меню', callback_data='cancel')
    return builder.as_markup()
