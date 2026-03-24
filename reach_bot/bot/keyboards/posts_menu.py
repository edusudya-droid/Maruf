from datetime import timezone, timedelta
from typing import List

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models import SourcePost

TASHKENT = timezone(timedelta(hours=5))


def posts_keyboard(posts: List[SourcePost]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for post in posts:
        dt = post.published_at.replace(tzinfo=timezone.utc).astimezone(TASHKENT)
        date_str = dt.strftime("%Y-%m-%d %H:%M")
        short_text = (post.post_text or "")[:100].replace("\n", " ")
        views = f"{post.views_count:,}" if post.views_count else "?"
        label = f"📅 {date_str} | 👁{views} | {short_text}..."
        builder.button(text=label, callback_data=f"select_post:{post.id}")
    builder.adjust(1)
    return builder.as_markup()


def post_action_keyboard(post_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Analiz boshlash", callback_data=f"start_analyze:{post_id}")
    builder.button(text="📊 Hisobotni ko'rish", callback_data=f"view_report:{post_id}")
    builder.button(text="↩️ Orqaga", callback_data="back_to_posts")
    builder.adjust(1)
    return builder.as_markup()
