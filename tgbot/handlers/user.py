from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import bot
from services import ensure_user_subscription
from tgbot.keyboards.inline import keyboard_help, keyboard_start, keyboard_subscription

user_router = Router()


@user_router.message(Command('start'))
async def user_start(message: Message):
    is_subscribed, error_text = await ensure_user_subscription(bot, message.from_user)
    if not is_subscribed:
        await message.answer(
            '👋 Привет! Я выдаю VPN только подписчикам канала.\n\n'
            f'{error_text}',
            reply_markup=keyboard_subscription(),
            disable_web_page_preview=True,
        )
        return

    await message.answer(
        '👋 Привет! Я помогу быстро получить доступ к VPN.\n\n'
        'Как это работает:\n'
        '• подписка на канал обязательна\n'
        '• после подписки доступен пробный период на 1 день\n'
        '• дальше доступ продлевается оплатой 250 ₽ за 30 дней\n'
        '• подключение доступно для Android, iPhone, Mac, Windows и других устройств',
        reply_markup=keyboard_start(),
        disable_web_page_preview=True,
    )


@user_router.message(Command('help'))
async def help_handler(message: Message):
    await message.answer(
        'ℹ️ Бот выдает готовую subscription-ссылку для VPN на базе Xray только подписчикам канала.\n\n'
        'Подключение занимает меньше минуты:\n'
        '• 📢 подпишитесь на канал\n'
        '• ✅ подтвердите доступ в боте\n'
        '• 🎁 получите пробный доступ на 1 день\n'
        '• 📲 выберите устройство и подключитесь\n'
        '• 💳 для продления оплатите 250 ₽ за 30 дней\n\n'
        'После проверки бот сразу покажет все нужные данные для подключения.',
        reply_markup=keyboard_help(),
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data == 'help')
async def help_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await bot.send_message(
        callback_query.from_user.id,
        'ℹ️ Бот выдает готовую subscription-ссылку для VPN на базе Xray только подписчикам канала.\n\n'
        'Подключение занимает меньше минуты:\n'
        '• 📢 подпишитесь на канал\n'
        '• ✅ подтвердите доступ в боте\n'
        '• 🎁 получите пробный доступ на 1 день\n'
        '• 📲 выберите устройство и подключитесь\n'
        '• 💳 для продления оплатите 250 ₽ за 30 дней\n\n'
        'После проверки бот сразу покажет все нужные данные для подключения.',
        reply_markup=keyboard_help(),
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data == 'check_subscription')
async def check_subscription_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    is_subscribed, error_text = await ensure_user_subscription(bot, callback_query.from_user)
    if is_subscribed:
        await bot.send_message(
            callback_query.from_user.id,
            '✅ Подписка подтверждена. Теперь можно получить VPN.',
            reply_markup=keyboard_start(),
        )
        return

    await bot.send_message(
        callback_query.from_user.id,
        error_text or '⚠️ Подписка пока не подтверждена.',
        reply_markup=keyboard_subscription(),
    )
