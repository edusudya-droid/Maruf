from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from domain.enums import UserRole


def main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    r = UserRole(role)

    # All roles
    builder.button(text="📋 Hisobotlar /report")
    builder.button(text="📜 Tarix /history")

    if r in (UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.ANALYST):
        builder.button(text="📰 Postlar /posts")
        builder.button(text="🔍 Analiz /analyze")

    if r in (UserRole.SUPERADMIN, UserRole.ADMIN):
        builder.button(text="⚙️ Sozlamalar /settings")
        builder.button(text="📝 Loglar /logs")

    if r == UserRole.SUPERADMIN:
        builder.button(text="👥 Foydalanuvchilar /users")

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
