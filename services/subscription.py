import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.types import User

from loader import config
from services.user_store import user_store

logger = logging.getLogger(__name__)


async def ensure_user_subscription(bot: Bot, user: User) -> tuple[bool, str | None]:
    user_store.upsert_user(user)
    stored_user = user_store.get_user(user.id)
    if stored_user and stored_user.is_banned_forever:
        return False, (
            "🚫 Доступ к боту закрыт навсегда.\n\n"
            "Система зафиксировала отмену подписки после получения доступа.\n"
            "Повторная выдача VPN больше недоступна."
        )

    if not config.subscription.required:
        user_store.mark_subscribed(user.id)
        return True, None

    try:
        member = await bot.get_chat_member(
            chat_id=config.subscription.channel_id,
            user_id=user.id,
        )
    except TelegramAPIError as exc:
        logger.exception("Failed to check channel subscription")
        return False, (
            "Не получилось проверить подписку на канал. "
            "Проверьте, что бот добавлен в канал и имеет доступ к участникам."
        )

    if member.status in {
        ChatMemberStatus.CREATOR,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
    }:
        user_store.mark_subscribed(user.id)
        return True, None

    if member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False):
        user_store.mark_subscribed(user.id)
        return True, None

    if stored_user and stored_user.was_subscribed and not stored_user.is_banned_forever:
        user_store.ban_forever(user.id, "User unsubscribed after getting access")
        return False, (
            "🚫 Доступ к боту закрыт навсегда.\n\n"
            "Система зафиксировала отмену подписки после получения доступа.\n"
            "Повторная выдача VPN больше недоступна."
        )

    return False, "Сначала подпишитесь на канал, потом нажмите кнопку проверки."
