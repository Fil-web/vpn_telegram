from html import escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import bot
from services import (
    ensure_user_subscription,
    get_connect_page_link,
    get_ios_app_link,
    get_manual_page_link,
    get_vpn_access_text,
    xui_service,
)
from tgbot.keyboards.inline import keyboard_subscription, keyboard_vpn_access

vpn_router = Router()


async def _send_vpn_access(user):
    is_subscribed, error_text = await ensure_user_subscription(bot, user)
    if not is_subscribed:
        await bot.send_message(
            user.id,
            error_text or 'Сначала подпишитесь на канал.',
            reply_markup=keyboard_subscription(),
        )
        return

    try:
        if xui_service.is_enabled():
            access_data = await xui_service.get_or_create_access(user)
        else:
            access_data = get_vpn_access_text()
    except RuntimeError as exc:
        await bot.send_message(user.id, str(exc))
        return

    android_connect_link = get_connect_page_link(access_data)
    ios_app_link = get_ios_app_link()
    android_manual_link = get_manual_page_link(access_data, "android")
    ios_manual_link = get_manual_page_link(access_data, "ios")

    await bot.send_message(
        user.id,
        '🚀 VPN готов к подключению.\n\n'
        'Доступ выдается только участникам закрытого чата и подписчикам канала.\n'
        'Выберите свое устройство:\n'
        '• для Android доступно быстрое подключение в v2RayTun\n'
        '• для iPhone доступно приложение V2Ray Client и ручное добавление\n\n'
        f'<pre>{escape(access_data)}</pre>',
        reply_markup=keyboard_vpn_access(
            android_connect_link=android_connect_link,
            ios_app_link=ios_app_link,
            android_manual_link=android_manual_link,
            ios_manual_link=ios_manual_link,
        ),
    )


@vpn_router.message(Command('vpn'))
async def vpn_handler(message: Message):
    await _send_vpn_access(message.from_user)


@vpn_router.callback_query(F.data == 'vpn')
async def vpn_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await _send_vpn_access(callback_query.from_user)
