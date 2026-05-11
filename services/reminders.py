from datetime import datetime, timedelta, timezone

from aiogram import Bot

from loader import config
from services.user_store import StoredUser, user_store
from tgbot.keyboards.inline import keyboard_payment_required


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _days_left(user: StoredUser) -> timedelta | None:
    access_until = user.access_until_dt
    if not access_until:
        return None
    if access_until <= _utc_now():
        return None
    return access_until - _utc_now()


def _reminder_text(days: int) -> str:
    day_word = "дня" if days == 2 else "день"
    if days == 2:
        return (
            f"✨ Доступ к VPN закончится через {days} {day_word}.\n\n"
            "Чтобы не остаться без подключения в неудобный момент, лучше продлить доступ заранее.\n\n"
            f"💳 Продление: {config.access_policy.price_rub} ₽\n"
            f"📅 Новый период: {config.access_policy.paid_duration_days} дней\n"
            f"📦 Лимит на период: {config.access_policy.paid_traffic_gb} ГБ"
        )
    return (
        f"⏰ До окончания доступа остался {days} {day_word}.\n\n"
        "Если хотите пользоваться VPN без паузы, продлите доступ сейчас. После оплаты всё активируется автоматически.\n\n"
        f"💳 Продление: {config.access_policy.price_rub} ₽\n"
        f"📅 Новый период: {config.access_policy.paid_duration_days} дней\n"
        f"📦 Лимит на период: {config.access_policy.paid_traffic_gb} ГБ"
    )


def _should_send_two_day(user: StoredUser) -> bool:
    if user.is_banned_forever or user.reminder_two_day_sent_at:
        return False
    delta = _days_left(user)
    if not delta:
        return False
    return timedelta(days=1) < delta <= timedelta(days=2)


def _should_send_one_day(user: StoredUser) -> bool:
    if user.is_banned_forever or user.reminder_one_day_sent_at:
        return False
    delta = _days_left(user)
    if not delta:
        return False
    return timedelta(0) < delta <= timedelta(days=1)


async def send_expiry_reminders(bot: Bot) -> None:
    for user in [item for item in user_store.list_users() if item]:
        if _should_send_two_day(user):
            try:
                await bot.send_message(
                    user.telegram_id,
                    _reminder_text(2),
                    reply_markup=keyboard_payment_required(),
                )
                user_store.mark_reminder_sent(user.telegram_id, "2d")
            except Exception:
                continue

        if _should_send_one_day(user):
            try:
                await bot.send_message(
                    user.telegram_id,
                    _reminder_text(1),
                    reply_markup=keyboard_payment_required(),
                )
                user_store.mark_reminder_sent(user.telegram_id, "1d")
            except Exception:
                continue
