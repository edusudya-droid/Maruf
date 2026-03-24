from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from domain.enums import UserRole


def main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    r = UserRole(role)

    # All roles
    builder.button(text="/report")
    builder.button(text="/history")

    if r in (UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.ANALYST):
        builder.button(text="/posts")
        builder.button(text="/analyze")

    if r in (UserRole.SUPERADMIN, UserRole.ADMIN):
        builder.button(text="/settings")
        builder.button(text="/logs")

    if r == UserRole.SUPERADMIN:
        builder.button(text="/users")

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
