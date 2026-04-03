from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import bot
from services import ensure_user_subscription
from tgbot.keyboards.inline import keyboard_start, keyboard_help, keyboard_subscription

user_router = Router()


@user_router.message(Command('start'))
async def user_start(message: Message):
    is_subscribed, error_text = await ensure_user_subscription(bot, message.from_user)
    if not is_subscribed:
        await message.answer(
            '👋 Привет! Я выдаю VPN только участникам закрытого чата и подписчикам канала.\n\n'
            f'{error_text}',
            reply_markup=keyboard_subscription(),
            disable_web_page_preview=True,
        )
        return

    await message.answer(
        '👋 Привет! Я помогу тебе быстро подключиться к VPN на базе Xray.\n\n'
        'Доступ получают только участники закрытого чата и подписчики канала.\n\n'
        'Ты получишь готовую subscription-ссылку и сможешь подключиться в пару нажатий через v2RayTun или вручную через любой совместимый Xray-клиент.',
        reply_markup=keyboard_start(),
        disable_web_page_preview=True,
    )


@user_router.message(Command('help'))
async def help_handler(message: Message):
    await message.answer(
        'ℹ️ Бот выдает готовую subscription-ссылку для VPN на базе Xray только участникам закрытого чата и подписчикам канала.\n\n'
        'Подключение занимает меньше минуты:\n'
        '• 💬 вступите в закрытый чат\n'
        '• 📢 подпишитесь на канал\n'
        '• ✅ подтвердите доступ в боте\n'
        '• 📲 можно открыть конфиг в v2RayTun автоматически\n'
        '• 🛠 можно добавить VPN вручную в любой совместимый Xray-клиент\n\n'
        'После проверки бот сразу покажет все нужные данные для подключения.',
        reply_markup=keyboard_help(),
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data == 'help')
async def help_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await bot.send_message(
        callback_query.from_user.id,
        'ℹ️ Бот выдает готовую subscription-ссылку для VPN на базе Xray только участникам закрытого чата и подписчикам канала.\n\n'
        'Подключение занимает меньше минуты:\n'
        '• 💬 вступите в закрытый чат\n'
        '• 📢 подпишитесь на канал\n'
        '• ✅ подтвердите доступ в боте\n'
        '• 📲 можно открыть конфиг в v2RayTun автоматически\n'
        '• 🛠 можно добавить VPN вручную в любой совместимый Xray-клиент\n\n'
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
            '✅ Доступ подтвержден. Теперь можно получить VPN.',
            reply_markup=keyboard_start(),
        )
        return

    await bot.send_message(
        callback_query.from_user.id,
        error_text or '⚠️ Подписка пока не подтверждена.',
        reply_markup=keyboard_subscription(),
    )
