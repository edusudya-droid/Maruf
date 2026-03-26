from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.exceptions import InvalidSettingValueError, SettingNotFoundError, ok, err
from infrastructure.repositories.log_repo import AuditLogRepo
from infrastructure.repositories.settings_repo import SettingsRepo

ALLOWED_KEYS = {
    "near_full_similarity_threshold",
    "unavailable_retry_limit",
    "history_retention_days",
    "max_daily_analyses",
    "max_visible_posts",
}


async def get_all_settings(session: AsyncSession) -> dict:
    repo = SettingsRepo(session)
    settings = await repo.list_all()
    return ok(data={s.setting_key: s.setting_value for s in settings})


async def get_setting(key: str, session: AsyncSession) -> dict:
    if key not in ALLOWED_KEYS:
        return err(SettingNotFoundError(f"Sozlama topilmadi: {key}"))
    repo = SettingsRepo(session)
    setting = await repo.get(key)
    if not setting:
        return err(SettingNotFoundError())
    return ok(data={"key": setting.setting_key, "value": setting.setting_value})


async def update_setting(
    key: str,
    value: str,
    session: AsyncSession,
    updated_by_user_id: Optional[int] = None,
) -> dict:
    if key not in ALLOWED_KEYS:
        return err(SettingNotFoundError(f"Ruxsat etilmagan sozlama: {key}"))

    # Validate value
    try:
        _validate(key, value)
    except ValueError as exc:
        return err(InvalidSettingValueError(str(exc)))

    repo = SettingsRepo(session)
    await repo.set(key, value, updated_by_user_id=updated_by_user_id)

    log_repo = AuditLogRepo(session)
    await log_repo.create(
        action_type="SETTING_CHANGED",
        user_id=updated_by_user_id,
        object_type="SystemSetting",
        object_id=key,
        details=f"New value: {value}",
    )
    await session.commit()
    return ok()


def _validate(key: str, value: str) -> None:
    if key == "near_full_similarity_threshold":
        f = float(value)
        if not (0 < f <= 1):
            raise ValueError("Threshold 0 < x <= 1 bo'lishi kerak")
    elif key in ("unavailable_retry_limit", "max_daily_analyses", "max_visible_posts"):
        i = int(value)
        if i < 0:
            raise ValueError("Qiymat manfiy bo'lmasligi kerak")
    elif key == "history_retention_days":
        if value != "null":
            i = int(value)
            if i <= 0:
                raise ValueError("Kunlar 0 dan katta bo'lishi kerak")
