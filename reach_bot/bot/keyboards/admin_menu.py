from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List


def users_list_keyboard(users: List[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in users:
        name = u.get("full_name") or u.get("username") or str(u["telegram_user_id"])
        status_icon = "✅" if u["status"] == "ACTIVE" else "🚫"
        builder.button(
            text=f"{status_icon} {name} [{u['role']}]",
            callback_data=f"user_detail:{u['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def user_actions_keyboard(user_id: int, current_status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if current_status == "ACTIVE":
        builder.button(text="🚫 Bloklash", callback_data=f"block_user:{user_id}")
    else:
        builder.button(text="✅ Blokdan chiqarish", callback_data=f"unblock_user:{user_id}")
    builder.button(text="🔄 Rolni o'zgartirish", callback_data=f"change_role:{user_id}")
    builder.button(text="↩️ Orqaga", callback_data="back_to_users")
    builder.adjust(1)
    return builder.as_markup()


def roles_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for role in ["SUPERADMIN", "ADMIN", "ANALYST", "VIEWER"]:
        builder.button(text=role, callback_data=f"set_role:{user_id}:{role}")
    builder.button(text="↩️ Bekor qilish", callback_data=f"user_detail:{user_id}")
    builder.adjust(2)
    return builder.as_markup()


def settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, value in settings.items():
        builder.button(text=f"✏️ {key}: {value}", callback_data=f"edit_setting:{key}")
    builder.adjust(1)
    return builder.as_markup()
