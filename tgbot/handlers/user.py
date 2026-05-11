from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import bot
from services import ensure_user_subscription, get_access_state
from services.user_store import user_store
from tgbot.keyboards.inline import keyboard_help, keyboard_start, keyboard_subscription

user_router = Router()


@user_router.message(Command('start'))
async def user_start(message: Message):
    is_subscribed, error_text = await ensure_user_subscription(bot, message.from_user)
    if not is_subscribed:
        await message.answer(
            '👋 Привет! Здесь можно быстро получить VPN-доступ.\n\n'
            'Чтобы начать, нужна только подписка на канал.\n\n'
            f'{error_text}',
            reply_markup=keyboard_subscription(),
            disable_web_page_preview=True,
        )
        return

    stored_user = user_store.get_user(message.from_user.id)
    has_active_access = get_access_state(stored_user) == "active"

    await message.answer(
        '👋 Привет! Здесь можно быстро подключить VPN без лишней настройки.\n\n'
        'Что вы получите:\n'
        '• доступ на 30 дней\n'
        '• 50 ГБ трафика\n'
        '• одну ссылку для всех устройств\n\n'
        'Что дальше:\n'
        '• нажмите «Открыть доступ»\n'
        '• оплатите 250 ₽\n'
        '• сразу получите готовое подключение',
        reply_markup=keyboard_start(has_active_access=has_active_access),
        disable_web_page_preview=True,
    )


@user_router.message(Command('help'))
async def help_handler(message: Message):
    await message.answer(
        '❓ Как подключиться\n\n'
        '1. Подпишитесь на канал.\n'
        '2. Откройте доступ в боте.\n'
        '3. Оплатите 250 ₽.\n'
        '4. Выберите свое устройство и подключитесь.\n\n'
        'В доступ входит 30 дней использования и 50 ГБ трафика.\n'
        'После оплаты бот сразу покажет готовую ссылку и кнопки подключения.',
        reply_markup=keyboard_help(),
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data == 'help')
async def help_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await bot.send_message(
        callback_query.from_user.id,
        '❓ Как подключиться\n\n'
        '1. Подпишитесь на канал.\n'
        '2. Откройте доступ в боте.\n'
        '3. Оплатите 250 ₽.\n'
        '4. Выберите свое устройство и подключитесь.\n\n'
        'В доступ входит 30 дней использования и 50 ГБ трафика.\n'
        'После оплаты бот сразу покажет готовую ссылку и кнопки подключения.',
        reply_markup=keyboard_help(),
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data == 'check_subscription')
async def check_subscription_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    is_subscribed, error_text = await ensure_user_subscription(bot, callback_query.from_user)
    if is_subscribed:
        stored_user = user_store.get_user(callback_query.from_user.id)
        has_active_access = get_access_state(stored_user) == "active"
        await bot.send_message(
            callback_query.from_user.id,
            '✅ Подписка подтверждена. Теперь можно открыть доступ к VPN.',
            reply_markup=keyboard_start(has_active_access=has_active_access),
        )
        return

    await bot.send_message(
        callback_query.from_user.id,
        error_text or '⚠️ Подписка пока не подтверждена.',
        reply_markup=keyboard_subscription(),
    )
