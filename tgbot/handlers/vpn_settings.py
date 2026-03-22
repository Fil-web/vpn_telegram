from html import escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import bot
from services import ensure_user_subscription, get_v2raytun_import_link, get_vpn_access_text
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
        access_data = get_vpn_access_text()
    except RuntimeError as exc:
        await bot.send_message(user.id, str(exc))
        return

    v2raytun_link = get_v2raytun_import_link(access_data)

    await bot.send_message(
        user.id,
        'Ваши данные для подключения:\n\n'
        f'<pre>{escape(access_data)}</pre>\n\n'
        'Если у вас установлен v2RayTun, можно открыть конфиг кнопкой ниже.',
        reply_markup=keyboard_vpn_access(v2raytun_link),
    )


@vpn_router.message(Command('vpn'))
async def vpn_handler(message: Message):
    await _send_vpn_access(message.from_user)


@vpn_router.callback_query(F.data == 'vpn')
async def vpn_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await _send_vpn_access(callback_query.from_user)
