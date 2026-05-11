from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import config
from services.user_store import user_store
from services.xui_api import xui_service
from tgbot.keyboards.inline import keyboard_admin, keyboard_admin_user_actions, keyboard_admin_users

admin_router = Router()


def _is_admin(message: Message) -> bool:
    return message.from_user.id == config.tg_bot.admin_id


def _is_admin_callback(callback_query: CallbackQuery) -> bool:
    return callback_query.from_user.id == config.tg_bot.admin_id


def _users_text() -> str:
    users = [user for user in user_store.list_users() if user]
    if not users:
        return "Пока нет сохраненных пользователей."

    lines = ["👥 Пользователи:", "", "Ниже кнопки по последним 15 пользователям."]
    for user in users[:15]:
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
        "Кнопки ниже показывают пользователей и вечные баны.\n"
        "Из карточки пользователя можно подарить VPN на 1, 7 или 30 дней.\n\n"
        "Ручные команды:\n"
        "/admin — открыть админку\n"
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
    reply_markup=None,
) -> None:
    await callback_query.answer()
    try:
        await callback_query.message.edit_text(text, reply_markup=reply_markup or keyboard_admin())
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


def _recent_users() -> list:
    return [user for user in user_store.list_users()[:15] if user]


def _user_card_text(user_id: int) -> str:
    user = user_store.get_user(user_id)
    if not user:
        return "Пользователь не найден."

    status = "🚫 Бан" if user.is_banned_forever else ("✅ Доступ подтвержден" if user.was_subscribed else "🆕 Новый")
    vpn_status = "есть" if user.xui_sub_id else "нет"
    return (
        "👤 Карточка пользователя\n\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Username: @{user.username or '-'}\n"
        f"Имя: {user.first_name or '-'}\n"
        f"Статус: {status}\n"
        f"VPN: {vpn_status}\n"
        f"Sub ID: <code>{user.xui_sub_id or '-'}</code>\n"
        f"Создан: {user.created_at[:19].replace('T', ' ')}"
    )


@admin_router.message(Command("admin"))
async def admin_menu_handler(message: Message):
    if not _is_admin(message):
        return

    await message.answer(_admin_menu_text(), reply_markup=keyboard_admin())


@admin_router.message(Command("users"))
async def users_handler(message: Message):
    if not _is_admin(message):
        return

    await message.answer(_users_text(), reply_markup=keyboard_admin_users(_recent_users()))


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
    await _show_admin_screen(
        callback_query,
        _users_text(),
        reply_markup=keyboard_admin_users(_recent_users()),
    )


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


@admin_router.callback_query(F.data.startswith("admin_user:"))
async def admin_user_callback(callback_query: CallbackQuery):
    if not _is_admin_callback(callback_query):
        return
    _, user_id_raw = callback_query.data.split(":", maxsplit=1)
    user_id = int(user_id_raw)
    user = user_store.get_user(user_id)
    await _show_admin_screen(
        callback_query,
        _user_card_text(user_id),
        reply_markup=keyboard_admin_user_actions(
            user_id,
            is_banned=bool(user and user.is_banned_forever),
        ),
    )


@admin_router.callback_query(F.data.startswith("admin_gift:"))
async def admin_gift_callback(callback_query: CallbackQuery):
    if not _is_admin_callback(callback_query):
        return
    _, days_raw, user_id_raw = callback_query.data.split(":", maxsplit=2)
    days = int(days_raw)
    user_id = int(user_id_raw)
    stored_user = user_store.get_user(user_id)
    if not stored_user:
        await _show_admin_screen(callback_query, "Пользователь не найден.")
        return

    plan_map = {
        1: config.xui.gift_day_plan,
        7: config.xui.gift_week_plan,
        30: config.xui.gift_month_plan,
    }
    plan = plan_map.get(days)
    if not plan:
        await _show_admin_screen(callback_query, "Неизвестный период подарка.")
        return

    try:
        grant_result = await xui_service.grant_plan(stored_user, plan)
    except RuntimeError as exc:
        await _show_admin_screen(
            callback_query,
            f"Не удалось выдать подарок.\n\n{exc}",
            reply_markup=keyboard_admin_user_actions(user_id, is_banned=stored_user.is_banned_forever),
        )
        return

    user_store.set_access_period(
        stored_user.telegram_id,
        access_until=grant_result.expires_at.isoformat(),
        access_kind="gift",
        trial_started_at=stored_user.trial_started_at,
    )

    await _show_admin_screen(
        callback_query,
        (
            "🎁 Подарок выдан\n\n"
            f"Пользователь: <code>{stored_user.telegram_id}</code>\n"
            f"Период: {grant_result.duration_days} дн.\n"
            f"Трафик: {grant_result.traffic_gb} ГБ\n"
            f"Действует до: {grant_result.expires_at.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}"
        ),
        reply_markup=keyboard_admin_user_actions(user_id, is_banned=stored_user.is_banned_forever),
    )


@admin_router.callback_query(F.data.startswith("admin_ban:"))
async def admin_ban_callback(callback_query: CallbackQuery):
    if not _is_admin_callback(callback_query):
        return
    _, user_id_raw = callback_query.data.split(":", maxsplit=1)
    user_id = int(user_id_raw)
    user_store.unban(user_id)
    user_store.ban_forever(user_id, "Manual admin ban")
    stored_user = user_store.get_user(user_id)
    if stored_user:
        try:
            await xui_service.disable_user(stored_user)
        except Exception:
            pass
    await _show_admin_screen(
        callback_query,
        f"🚫 Пользователь <code>{user_id}</code> заблокирован.",
        reply_markup=keyboard_admin_user_actions(user_id, is_banned=True),
    )


@admin_router.callback_query(F.data.startswith("admin_unban:"))
async def admin_unban_callback(callback_query: CallbackQuery):
    if not _is_admin_callback(callback_query):
        return
    _, user_id_raw = callback_query.data.split(":", maxsplit=1)
    user_id = int(user_id_raw)
    user_store.unban(user_id)
    await _show_admin_screen(
        callback_query,
        f"✅ Пользователь <code>{user_id}</code> разблокирован.",
        reply_markup=keyboard_admin_user_actions(user_id, is_banned=False),
    )
