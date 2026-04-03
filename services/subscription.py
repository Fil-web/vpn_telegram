import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.types import User

from loader import config
from services.user_store import user_store
from services.xui_api import xui_service

logger = logging.getLogger(__name__)


async def _check_membership(bot: Bot, chat_id: str, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    if member.status in {
        ChatMemberStatus.CREATOR,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
    }:
        return True
    return member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False)


async def ensure_user_subscription(bot: Bot, user: User) -> tuple[bool, str | None]:
    user_store.upsert_user(user)
    stored_user = user_store.get_user(user.id)
    if stored_user and stored_user.is_banned_forever:
        return False, (
            "🚫 Доступ к боту закрыт навсегда.\n\n"
            "Система зафиксировала отмену подписки после получения доступа.\n"
            "Повторная выдача VPN больше недоступна."
        )

    try:
        if config.access_chat.required:
            is_chat_member = await _check_membership(bot, config.access_chat.chat_id, user.id)
            if not is_chat_member:
                return False, (
                    "Сначала вступите в закрытый чат, потом вернитесь в бота и нажмите проверку."
                )

        if not config.subscription.required:
            user_store.mark_subscribed(user.id)
            return True, None

        is_channel_member = await _check_membership(
            bot,
            config.subscription.channel_id,
            user.id,
        )
    except TelegramAPIError as exc:
        logger.exception("Failed to check access requirements")
        return False, (
            "Не получилось проверить доступ. "
            "Проверьте, что бот добавлен в чат и канал и имеет доступ к участникам."
        )

    if is_channel_member:
        user_store.mark_subscribed(user.id)
        return True, None

    if stored_user and stored_user.was_subscribed and not stored_user.is_banned_forever:
        user_store.ban_forever(user.id, "User unsubscribed after getting access")
        updated_user = user_store.get_user(user.id)
        if updated_user:
            try:
                await xui_service.disable_user(updated_user)
            except Exception:
                logger.exception("Failed to disable x-ui client for unsubscribed user")
        return False, (
            "🚫 Доступ к боту закрыт навсегда.\n\n"
            "Система зафиксировала отмену подписки после получения доступа.\n"
            "Повторная выдача VPN больше недоступна."
        )

    if config.access_chat.required:
        return False, (
            "Сначала вступите в закрытый чат и подпишитесь на канал, потом нажмите кнопку проверки."
        )

    return False, "Сначала подпишитесь на канал, потом нажмите кнопку проверки."
