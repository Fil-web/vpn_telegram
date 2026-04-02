from html import escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import bot
from services import ensure_user_subscription, get_connect_page_link, get_manual_page_link, get_vpn_access_text, xui_service
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

    connect_page_link = get_connect_page_link(access_data)
    manual_page_link = get_manual_page_link(access_data)

    await bot.send_message(
        user.id,
        '🚀 VPN готов к подключению.\n\n'
        'Ниже находится ваша subscription-ссылка. Можно открыть ее в v2RayTun автоматически или добавить вручную.\n\n'
        f'<pre>{escape(access_data)}</pre>',
        reply_markup=keyboard_vpn_access(connect_page_link, manual_page_link),
    )


@vpn_router.message(Command('vpn'))
async def vpn_handler(message: Message):
    await _send_vpn_access(message.from_user)


@vpn_router.callback_query(F.data == 'vpn')
async def vpn_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await _send_vpn_access(callback_query.from_user)
