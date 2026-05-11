from datetime import datetime, timedelta, timezone

from aiogram.types import User

from loader import config
from services.user_store import StoredUser, user_store
from services.xui_api import xui_service


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _trial_plan() -> config.xui.Plan:
    return config.xui.Plan(
        traffic_gb=config.access_policy.trial_traffic_gb,
        duration_days=config.access_policy.trial_duration_days,
    )


def _paid_plan() -> config.xui.Plan:
    return config.xui.Plan(
        traffic_gb=config.access_policy.paid_traffic_gb,
        duration_days=config.access_policy.paid_duration_days,
    )


async def ensure_trial_access(user: User) -> tuple[StoredUser, str]:
    access_text = await xui_service.get_or_create_access(user)
    stored_user = user_store.get_user(user.id)
    if not stored_user:
        raise RuntimeError("Пользователь не найден в базе после выдачи VPN.")
    grant_result = await xui_service.grant_plan(stored_user, _trial_plan())
    trial_started_at = _utc_now().isoformat()
    user_store.set_access_period(
        user.id,
        access_until=grant_result.expires_at.isoformat(),
        access_kind="trial",
        trial_started_at=trial_started_at,
    )
    refreshed_user = user_store.get_user(user.id)
    if not refreshed_user:
        raise RuntimeError("Пользователь не найден после обновления trial-доступа.")
    return refreshed_user, access_text


async def ensure_paid_access(stored_user: StoredUser) -> tuple[StoredUser, str]:
    user = xui_service._user_from_stored(stored_user)
    access_text = await xui_service.get_or_create_access(user)
    refreshed = user_store.get_user(stored_user.telegram_id)
    if not refreshed:
        raise RuntimeError("Пользователь не найден после обновления VPN-профиля.")
    grant_result = await xui_service.grant_plan(refreshed, _paid_plan())
    user_store.set_access_period(
        refreshed.telegram_id,
        access_until=grant_result.expires_at.isoformat(),
        access_kind="paid",
        trial_started_at=refreshed.trial_started_at,
    )
    final_user = user_store.get_user(refreshed.telegram_id)
    if not final_user:
        raise RuntimeError("Пользователь не найден после обновления платного доступа.")
    return final_user, access_text


def get_access_state(stored_user: StoredUser | None) -> str:
    if not stored_user:
        return "new"
    if stored_user.is_banned_forever:
        return "banned"
    if stored_user.has_active_access:
        return "active"
    return "payment_required"
