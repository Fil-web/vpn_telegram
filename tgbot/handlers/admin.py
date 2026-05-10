from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import config
from services.user_store import user_store
from services.xui_api import xui_service
from tgbot.keyboards.inline import keyboard_admin

admin_router = Router()


def _is_admin(message: Message) -> bool:
    return message.from_user.id == config.tg_bot.admin_id


def _is_admin_callback(callback_query: CallbackQuery) -> bool:
    return callback_query.from_user.id == config.tg_bot.admin_id


def _users_text() -> str:
    users = [user for user in user_store.list_users() if user]
    if not users:
        return "Пока нет сохраненных пользователей."

    lines = ["👥 Пользователи:"]
    for user in users[:50]:
        status = "banned" if user.is_banned_forever else ("subscribed" if user.was_subscribed else "new")
        lines.append(f"{user.telegram_id} | @{user.username or '-'} | {status}")
    return "\n".join(lines)


def _banned_text() -> str:
    users = [user for user in user_store.list_banned() if user]
    if not users:
        return "🚫 Список вечных банов пуст."

    lines = ["🚫 Заблокированные навсегда:"]
    for user in users[:50]:
        lines.append(f"{user.telegram_id} | @{user.username or '-'} | {user.banned_reason or '-'}")
    return "\n".join(lines)


def _admin_help_text() -> str:
    return (
        "🛠 Админ-меню\n\n"
        "Кнопки ниже показывают пользователей и вечные баны.\n\n"
        "Ручные команды:\n"
        "/users — список пользователей\n"
        "/banned — список банов\n"
        "/ban 123456789 — заблокировать навсегда\n"
        "/unban 123456789 — снять бан"
    )


def _admin_menu_text() -> str:
    users = [user for user in user_store.list_users() if user]
    banned = [user for user in users if user.is_banned_forever]
    subscribed = [user for user in users if user.was_subscribed]
    xui_bound = [user for user in users if user.xui_sub_id]
    return (
        "🛠 Админ-панель\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"✅ С доступом: {len(subscribed)}\n"
        f"🔗 С выданным VPN: {len(xui_bound)}\n"
        f"🚫 В бане: {len(banned)}\n\n"
        "Выберите действие кнопками ниже."
    )


async def _show_admin_screen(
    callback_query: CallbackQuery,
    text: str,
) -> None:
    await callback_query.answer()
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard_admin())
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


@admin_router.message(Command("admin"))
async def admin_menu_handler(message: Message):
    if not _is_admin(message):
        return

    await message.answer(_admin_menu_text(), reply_markup=keyboard_admin())


@admin_router.message(Command("users"))
async def users_handler(message: Message):
    if not _is_admin(message):
        return

    await message.answer(_users_text(), reply_markup=keyboard_admin())


@admin_router.message(Command("banned"))
async def banned_handler(message: Message):
    if not _is_admin(message):
        return

    await message.answer(_banned_text(), reply_markup=keyboard_admin())


@admin_router.callback_query(F.data == "admin_menu")
async def admin_menu_callback(callback_query: CallbackQuery):
    if not _is_admin_callback(callback_query):
        return
    await _show_admin_screen(callback_query, _admin_menu_text())


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


@admin_router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback_query: CallbackQuery):
    if not _is_admin_callback(callback_query):
        return
    await _show_admin_screen(callback_query, _users_text())


@admin_router.callback_query(F.data == "admin_banned")
async def admin_banned_callback(callback_query: CallbackQuery):
    if not _is_admin_callback(callback_query):
        return
    await _show_admin_screen(callback_query, _banned_text())


@admin_router.callback_query(F.data == "admin_help")
async def admin_help_callback(callback_query: CallbackQuery):
    if not _is_admin_callback(callback_query):
        return
    await _show_admin_screen(callback_query, _admin_help_text())
