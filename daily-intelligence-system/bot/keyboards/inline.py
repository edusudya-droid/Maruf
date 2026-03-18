"""Inline klaviaturalar."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ])


def role_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 Tadbirkor", callback_data="role_entrepreneur")],
        [InlineKeyboardButton("📊 Analitik", callback_data="role_analyst")],
        [InlineKeyboardButton("⚖️ Yurist", callback_data="role_lawyer")],
        [InlineKeyboardButton("💰 Investor", callback_data="role_investor")],
        [InlineKeyboardButton("🏛️ Davlat xodimi", callback_data="role_official")],
        [InlineKeyboardButton("👤 Boshqa", callback_data="role_other")],
    ])


def topics_keyboard(selected: list[str] = None) -> InlineKeyboardMarkup:
    selected = selected or []
    topics = [
        ("iqtisodiyot", "economics"),
        ("qonunchilik", "law"),
        ("biznes", "business"),
        ("investitsiya", "investment"),
        ("xalqaro siyosat", "international"),
        ("texnologiya", "technology"),
        ("qishloq xo'jaligi", "agriculture"),
        ("infratuzilma", "infrastructure"),
    ]
    rows = []
    for label, value in topics:
        check = "✅ " if value in selected else ""
        rows.append([InlineKeyboardButton(f"{check}{label}", callback_data=f"topic_{value}")])
    rows.append([InlineKeyboardButton("✔️ Tayyor", callback_data="topics_done")])
    return InlineKeyboardMarkup(rows)


def format_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Qisqa (quick)", callback_data="format_quick")],
        [InlineKeyboardButton("📋 Standart", callback_data="format_standard")],
        [InlineKeyboardButton("📚 Kengaytirilgan", callback_data="format_extended")],
    ])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📰 So'nggi digest", callback_data="digest"),
            InlineKeyboardButton("🔍 Brief yaratish", callback_data="brief_menu"),
        ],
        [
            InlineKeyboardButton("📌 Mavzular", callback_data="topics_menu"),
            InlineKeyboardButton("⚙️ Sozlamalar", callback_data="settings_menu"),
        ],
        [
            InlineKeyboardButton("📁 Arxiv", callback_data="archive_menu"),
            InlineKeyboardButton("🔔 Ogohlantirishlar", callback_data="alerts_menu"),
        ],
    ])


def back_keyboard(callback: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Orqaga", callback_data=callback)]
    ])
