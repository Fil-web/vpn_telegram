from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from loader import config
from services.user_store import user_store
from services.xui_api import xui_service

admin_router = Router()


def _is_admin(message: Message) -> bool:
    return message.from_user.id == config.tg_bot.admin_id


@admin_router.message(Command("users"))
async def users_handler(message: Message):
    if not _is_admin(message):
        return

    users = [user for user in user_store.list_users() if user]
    if not users:
        await message.answer("Пока нет сохраненных пользователей.")
        return

    lines = ["👥 Пользователи:"]
    for user in users[:50]:
        status = "banned" if user.is_banned_forever else ("subscribed" if user.was_subscribed else "new")
        lines.append(f"{user.telegram_id} | @{user.username or '-'} | {status}")
    await message.answer("\n".join(lines))


@admin_router.message(Command("banned"))
async def banned_handler(message: Message):
    if not _is_admin(message):
        return

    users = [user for user in user_store.list_banned() if user]
    if not users:
        await message.answer("🚫 Список вечных банов пуст.")
        return

    lines = ["🚫 Заблокированные навсегда:"]
    for user in users[:50]:
        lines.append(f"{user.telegram_id} | @{user.username or '-'} | {user.banned_reason or '-'}")
    await message.answer("\n".join(lines))


@admin_router.message(Command("ban"))
async def ban_handler(message: Message):
    if not _is_admin(message):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /ban 123456789")
        return

    telegram_id = int(parts[1])
    user_store.unban(telegram_id)
    user_store.ban_forever(telegram_id, "Manual admin ban")
    stored_user = user_store.get_user(telegram_id)
    if stored_user:
        try:
            await xui_service.disable_user(stored_user)
        except Exception:
            pass
    await message.answer(f"🚫 Пользователь {telegram_id} заблокирован навсегда.")


@admin_router.message(Command("unban"))
async def unban_handler(message: Message):
    if not _is_admin(message):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /unban 123456789")
        return

    telegram_id = int(parts[1])
    user_store.unban(telegram_id)
    await message.answer(f"✅ Пользователь {telegram_id} разблокирован.")
