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
            '👋 Привет! Здесь можно быстро получить VPN-доступ.\n\n'
            'Чтобы начать, нужна только подписка на канал.\n\n'
            f'{error_text}',
            reply_markup=keyboard_subscription(),
            disable_web_page_preview=True,
        )
        return

    await message.answer(
        '👋 Привет! Здесь можно быстро получить стабильный VPN без лишней настройки.\n\n'
        'Как это работает:\n'
        '• подписываетесь на канал\n'
        '• оплачиваете доступ за 250 ₽ на 30 дней\n'
        '• получаете готовую ссылку сразу после оплаты\n'
        '• одна ссылка подходит для Android, iPhone, Mac, Windows и других устройств\n\n'
        'Нажмите кнопку ниже, и бот сам проведет вас дальше.',
        reply_markup=keyboard_start(),
        disable_web_page_preview=True,
    )


@user_router.message(Command('help'))
async def help_handler(message: Message):
    await message.answer(
        'ℹ️ Как это работает\n\n'
        'Подключение занимает меньше минуты:\n'
        '• 📢 подпишитесь на канал\n'
        '• ✅ подтвердите доступ в боте\n'
        '• 💳 оплатите доступ\n'
        '• 📲 выберите устройство и подключитесь в пару нажатий\n'
        '• 🔁 по окончании периода просто продлите доступ\n\n'
        'В оплаченный период входит 50 ГБ трафика. После проверки бот сразу покажет все нужные данные для подключения.',
        reply_markup=keyboard_help(),
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data == 'help')
async def help_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await bot.send_message(
        callback_query.from_user.id,
        'ℹ️ Как это работает\n\n'
        'Подключение занимает меньше минуты:\n'
        '• 📢 подпишитесь на канал\n'
        '• ✅ подтвердите доступ в боте\n'
        '• 💳 оплатите доступ\n'
        '• 📲 выберите устройство и подключитесь в пару нажатий\n'
        '• 🔁 по окончании периода просто продлите доступ\n\n'
        'В оплаченный период входит 50 ГБ трафика. После проверки бот сразу покажет все нужные данные для подключения.',
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
            '✅ Подписка подтверждена. Теперь можно активировать доступ к VPN.',
            reply_markup=keyboard_start(),
        )
        return

    await bot.send_message(
        callback_query.from_user.id,
        error_text or '⚠️ Подписка пока не подтверждена.',
        reply_markup=keyboard_subscription(),
    )
