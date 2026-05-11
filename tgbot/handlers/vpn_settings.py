import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from loader import bot, config
from services import (
    ensure_paid_access,
    ensure_user_subscription,
    get_access_state,
    get_connect_page_link,
    get_ios_app_link,
    get_manual_page_link,
    xui_service,
    yookassa_service,
)
from services.user_store import user_store
from tgbot.keyboards.inline import (
    keyboard_device_actions,
    keyboard_device_picker,
    keyboard_payment_checkout,
    keyboard_payment_required,
    keyboard_payment_rules,
    keyboard_subscription,
)

vpn_router = Router()
logger = logging.getLogger(__name__)

WINDOWS_APP_URL = "https://github.com/2dust/v2rayN/releases/latest"
MAC_APP_URL = "https://github.com/2dust/v2rayN/releases/latest"
OTHER_GUIDE_URL = "https://xtls.github.io/en/config/inbounds/vless.html"


def _access_summary() -> str:
    return (
        f"⏳ Срок доступа: {config.access_policy.paid_duration_days} дней\n"
        f"📦 Лимит трафика: {config.access_policy.paid_traffic_gb} ГБ на весь период\n"
        f"💳 Стоимость продления: {config.access_policy.price_rub} ₽ / месяц"
    )


def _payment_required_text() -> str:
    return (
        "💸 Доступ к VPN открывается после оплаты.\n\n"
        "Активируйте доступ и получите готовую ссылку для подключения без лишней настройки.\n\n"
        f"{_access_summary()}\n\n"
        "После оплаты доступ активируется автоматически, а ссылка будет готова сразу для ваших устройств."
    )


async def _load_access_text(user) -> str:
    if xui_service.is_enabled():
        return await xui_service.get_or_create_access(user)
    return ""


async def _show_device_picker(user, intro_text: str | None = None) -> None:
    access_data = await _load_access_text(user)
    text = intro_text or (
        "🚀 VPN готов к подключению.\n\n"
        f"{_access_summary()}\n\n"
        "Выберите устройство, и я покажу самый удобный способ подключения."
    )
    if access_data:
        text += f"\n\n<pre>{escape(access_data)}</pre>"
    await bot.send_message(
        user.id,
        text,
        reply_markup=keyboard_device_picker(),
    )


async def _send_paywall(user) -> None:
    await bot.send_message(
        user.id,
        _payment_required_text(),
        reply_markup=keyboard_payment_required(),
    )


async def _send_vpn_access(user) -> None:
    is_subscribed, error_text = await ensure_user_subscription(bot, user)
    if not is_subscribed:
        await bot.send_message(
            user.id,
            error_text or "Сначала подпишитесь на канал.",
            reply_markup=keyboard_subscription(),
        )
        return

    stored_user = user_store.get_user(user.id)
    state = get_access_state(stored_user)

    try:
        if state == "active":
            await _show_device_picker(user)
            return

        if state in {"new", "payment_required"}:
            await _send_paywall(user)
            return

        await bot.send_message(user.id, "Доступ сейчас недоступен.")
    except RuntimeError as exc:
        await bot.send_message(user.id, str(exc))
    except Exception:
        logger.exception("Failed to prepare VPN access for user %s", user.id)
        await bot.send_message(
            user.id,
            "Не удалось подготовить VPN прямо сейчас. Попробуйте еще раз через несколько секунд.",
        )


def _platform_text(platform: str) -> tuple[str, str | None, str | None]:
    texts = {
        "android": (
            "🤖 Android\n\n"
            "Самый удобный вариант для Android:\n\n"
            "1. Нажмите автоматическое подключение.\n"
            "2. Откроется v2RayTun и предложит импорт.\n"
            "3. Если не сработает, используйте ручное добавление ниже.",
            None,
            None,
        ),
        "ios": (
            "🍎 iPhone / iOS\n\n"
            "Для iPhone подключение тоже простое:\n\n"
            "1. Откройте приложение из App Store.\n"
            "2. Добавьте subscription-ссылку вручную.\n"
            "3. Если приложение уже установлено, просто скопируйте ссылку ниже.",
            get_ios_app_link(),
            "📲 Открыть приложение",
        ),
        "mac": (
            "💻 Mac\n\n"
            "Для Mac подойдет любой совместимый Xray-клиент:\n\n"
            "1. Скачайте совместимый Xray-клиент.\n"
            "2. Импортируйте subscription-ссылку.\n"
            "3. Если быстрый импорт не сработает, используйте ручную ссылку ниже.",
            MAC_APP_URL,
            "⬇️ Скачать клиент",
        ),
        "windows": (
            "🪟 Windows\n\n"
            "Для Windows рекомендую классический вариант:\n\n"
            "1. Скачайте v2rayN.\n"
            "2. Импортируйте subscription-ссылку.\n"
            "3. При необходимости воспользуйтесь ручным добавлением.",
            WINDOWS_APP_URL,
            "⬇️ Скачать клиент",
        ),
        "other": (
            "🛠 Другие устройства\n\n"
            "Используйте subscription-ссылку или ручное добавление в любой совместимый Xray-клиент.\n"
            "Если клиент поддерживает импорт по URL, вставьте subscription-ссылку целиком.",
            OTHER_GUIDE_URL,
            "📘 Краткая инструкция",
        ),
    }
    return texts.get(
        platform,
        (
            "Выберите устройство заново.",
            None,
            None,
        ),
    )


@vpn_router.message(Command("vpn"))
async def vpn_handler(message: Message):
    await _send_vpn_access(message.from_user)


@vpn_router.callback_query(F.data == "vpn")
async def vpn_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer("Готовлю VPN...", show_alert=False)
    await _send_vpn_access(callback_query.from_user)


@vpn_router.callback_query(F.data == "payment_rules")
async def payment_rules_callback(callback_query: CallbackQuery):
    await callback_query.answer()
    await bot.send_message(
        callback_query.from_user.id,
        config.access_policy.payment_rules_text,
        reply_markup=keyboard_payment_rules(),
    )


@vpn_router.callback_query(F.data == "buy_vpn")
async def buy_vpn_callback(callback_query: CallbackQuery):
    await callback_query.answer("Создаю ссылку на оплату...", show_alert=False)
    is_subscribed, error_text = await ensure_user_subscription(bot, callback_query.from_user)
    if not is_subscribed:
        await bot.send_message(
            callback_query.from_user.id,
            error_text or "Сначала подпишитесь на канал.",
            reply_markup=keyboard_subscription(),
        )
        return
    stored_user = user_store.get_user(callback_query.from_user.id)
    if not stored_user:
        user_store.upsert_user(callback_query.from_user)
        stored_user = user_store.get_user(callback_query.from_user.id)
    if not stored_user:
        await bot.send_message(callback_query.from_user.id, "Не удалось подготовить оплату, попробуйте еще раз.")
        return
    if not yookassa_service.is_enabled():
        await bot.send_message(
            callback_query.from_user.id,
            "Оплата временно недоступна. Попробуйте немного позже или напишите администратору.",
            reply_markup=keyboard_payment_required(),
        )
        return
    try:
        payment = await yookassa_service.create_payment(stored_user)
    except Exception as exc:
        logger.exception("Failed to create YooKassa payment for user %s", callback_query.from_user.id)
        await bot.send_message(callback_query.from_user.id, str(exc))
        return

    confirmation_url = ((payment.get("confirmation") or {}).get("confirmation_url")) or ""
    if not confirmation_url:
        await bot.send_message(callback_query.from_user.id, "Не удалось получить ссылку на оплату.")
        return

    await bot.send_message(
        callback_query.from_user.id,
        (
            "✨ Доступ готов к активации.\n\n"
            f"За {config.access_policy.price_rub} ₽ вы получаете:\n"
            f"• {config.access_policy.paid_duration_days} дней доступа\n"
            f"• {config.access_policy.paid_traffic_gb} ГБ трафика\n"
            "• одну рабочую ссылку для всех ваших устройств\n\n"
            "После оплаты доступ активируется автоматически. Если подтверждение немного задержится, просто нажмите «Проверить оплату»."
        ),
        reply_markup=keyboard_payment_checkout(confirmation_url),
    )


@vpn_router.callback_query(F.data == "check_payment")
async def check_payment_callback(callback_query: CallbackQuery):
    await callback_query.answer("Проверяю оплату...", show_alert=False)
    is_subscribed, error_text = await ensure_user_subscription(bot, callback_query.from_user)
    if not is_subscribed:
        await bot.send_message(
            callback_query.from_user.id,
            error_text or "Сначала подпишитесь на канал.",
            reply_markup=keyboard_subscription(),
        )
        return
    stored_user = user_store.get_user(callback_query.from_user.id)
    if not stored_user or not stored_user.last_payment_id:
        await bot.send_message(
            callback_query.from_user.id,
            "Платеж пока не найден. Если вы еще не оплачивали, сначала нажмите кнопку оплаты.",
            reply_markup=keyboard_payment_required(),
        )
        return

    try:
        payment = await yookassa_service.get_payment(stored_user.last_payment_id)
    except Exception:
        logger.exception("Failed to check YooKassa payment %s", stored_user.last_payment_id)
        await bot.send_message(callback_query.from_user.id, "Не удалось проверить платеж прямо сейчас.")
        return

    status = payment.get("status", "")
    user_store.set_payment_state(
        callback_query.from_user.id,
        payment_id=stored_user.last_payment_id,
        payment_status=status,
    )

    if status == "succeeded":
        refreshed_user = user_store.get_user(callback_query.from_user.id)
        if not refreshed_user:
            await bot.send_message(callback_query.from_user.id, "Не удалось обновить доступ после оплаты.")
            return
        await ensure_paid_access(refreshed_user)
        await _show_device_picker(
            callback_query.from_user,
            (
                "✅ Доступ активирован.\n\n"
                "Все готово: VPN уже подключен к вашему аккаунту.\n\n"
                f"Период доступа: {config.access_policy.paid_duration_days} дней\n"
                f"Лимит трафика: {config.access_policy.paid_traffic_gb} ГБ\n\n"
                "Выберите устройство и подключайтесь в удобном для себя формате."
            ),
        )
        return

    if status == "pending":
        await bot.send_message(
            callback_query.from_user.id,
            "⏳ Платеж еще в обработке. Обычно это занимает совсем немного времени.",
            reply_markup=keyboard_payment_required(),
        )
        return

    await bot.send_message(
        callback_query.from_user.id,
        f"Статус платежа: {status or 'неизвестно'}. Если оплата не прошла, создайте новый платеж.",
        reply_markup=keyboard_payment_required(),
    )


@vpn_router.callback_query(F.data.startswith("device:"))
async def device_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    is_subscribed, error_text = await ensure_user_subscription(bot, callback_query.from_user)
    if not is_subscribed:
        await bot.send_message(
            callback_query.from_user.id,
            error_text or "Сначала подпишитесь на канал.",
            reply_markup=keyboard_subscription(),
        )
        return
    platform = callback_query.data.split(":", maxsplit=1)[1]
    access_text = await _load_access_text(callback_query.from_user)
    manual_link = get_manual_page_link(access_text)
    auto_link = get_connect_page_link(access_text) if platform == "android" else None
    text, secondary_link, secondary_text = _platform_text(platform)
    await bot.send_message(
        callback_query.from_user.id,
        text,
        reply_markup=keyboard_device_actions(
            auto_link=auto_link,
            manual_link=manual_link,
            secondary_link=secondary_link,
            secondary_text=secondary_text,
        ),
    )
