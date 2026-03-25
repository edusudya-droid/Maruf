"""All user-facing message texts in one place."""

# Auth
ACCESS_GRANTED = "Ruxsat berildi. Menyudan amalni tanlang."
ACCESS_DENIED = "Sizda tizimga kirish huquqi yo'q. Administratorga murojaat qiling."
USER_BLOCKED = "Hisobingiz bloklangan. Administratorga murojaat qiling."
PERMISSION_DENIED = "Bu amalni bajarishga ruxsatingiz yo'q."

# Menu
MAIN_MENU = "Asosiy menyu:"
SELECT_ACTION = "Amalni tanlang:"

# Posts
POSTS_LOADING = "Postlar yuklanmoqda..."
POSTS_EMPTY = "Rasmiy kanalda postlar topilmadi."
POST_SELECTED = "Post tanlandi. Analiz boshlash uchun /analyze ni bosing."

# Analyze
ANALYZE_STARTED = (
    "Analiz ishga tushirildi. Natija tayyorlanganidan so'ng ko'rishingiz mumkin."
)
ANALYZE_ALREADY_RUNNING = "Bu post uchun analiz allaqachon bajarilmoqda."
ANALYZE_NO_POST = "Avval publikatsiyani tanlang: /posts"
ANALYZE_DAILY_LIMIT = "Kunlik analiz limiti tugadi. Ertaga qayta urinib ko'ring."
ANALYZE_PENDING = "Analiz navbatda kutmoqda..."
ANALYZE_RUNNING = "Analiz bajarilmoqda, iltimos kuting..."

# Report
REPORT_NOT_FOUND = "Hisobot topilmadi. Avval analiz boshlang."
REPORT_STILL_RUNNING = "Analiz hali tugalanmadi. Biroz kuting."

# Settings
SETTINGS_UPDATED = "Sozlama yangilandi."
SETTINGS_INVALID = "Noto'g'ri qiymat. Iltimos to'g'ri qiymat kiriting."
SETTINGS_NOT_FOUND = "Sozlama topilmadi."

# Users
USER_ADDED = "Foydalanuvchi muvaffaqiyatli qo'shildi."
USER_ALREADY_EXISTS = "Bu foydalanuvchi allaqachon tizimda mavjud."
USER_NOT_FOUND = "Foydalanuvchi topilmadi."
USER_BLOCKED_MSG = "Foydalanuvchi bloklandi."
USER_UNBLOCKED_MSG = "Foydalanuvchi blokdan chiqarildi."
USER_ROLE_CHANGED = "Foydalanuvchi roli o'zgartirildi."

# Generic
ERROR_OCCURRED = "Xato yuz berdi. Iltimos qayta urinib ko'ring."
CANCEL = "Bekor qilindi."

_STATUS_LABELS = {
    "COMPLETED": "✅ Muvaffaqiyatli",
    "COMPLETED_WITH_SKIPS": "⚠️ Qisman (ba'zi postlar o'tkazib yuborildi)",
    "FAILED": "❌ Xato bilan tugadi",
}


def format_report(
    post_url: str,
    source_views: int,
    counted_posts_count: int,
    confirmed_secondary_views: int,
    total_confirmed_reach: int,
    skipped_posts_count: int,
    finished_at: str,
    status: str = "COMPLETED",
    notes: str = "",
) -> str:
    status_label = _STATUS_LABELS.get(status, status)

    # Nol natijalarga izoh
    if counted_posts_count == 0 and source_views == 0:
        reach_comment = (
            "\n⚠️ <i>Ko'rishlar va repostlar aniqlanmadi. "
            "Telethon sozlanganligini tekshiring.</i>"
        )
    elif counted_posts_count == 0:
        reach_comment = (
            "\n<i>Qidiruv oynasida tasdiqlangan repost topilmadi. "
            "Bot a'zo kanallardagina qidiriladi.</i>"
        )
    else:
        reach_comment = ""

    notes_section = f"\n📋 <i>{notes}</i>" if notes else ""

    return (
        "📊 <b>TASDIQLANGAN QAMROV HISOBOTI</b>\n\n"
        f"🔗 Manba: {post_url}\n"
        f"📌 Holat: {status_label}\n\n"
        f"👁 Original ko'rishlar: <b>{source_views:,}</b>\n"
        f"📢 Tasdiqlangan tarqalishlar: <b>{counted_posts_count} ta</b>\n"
        f"➕ Ikkilamchi ko'rishlar: <b>{confirmed_secondary_views:,}</b>\n\n"
        f"<b>JAMI TASDIQLANGAN QAMROV: {total_confirmed_reach:,}</b>\n"
        f"{reach_comment}\n"
        f"⏭ O'tkazib yuborilganlar: {skipped_posts_count} ta\n"
        f"🕐 Hisoblash vaqti: {finished_at}"
        f"{notes_section}\n\n"
        "<i>Faqat Telethon akkaunti a'zo bo'lgan kanallarda qidiriladigan "
        "tasdiqlangan ma'lumotlar asosida hisoblandi.</i>"
    )


def format_detected_post_line(
    status: str,
    post_url: str,
    views_count,
    confirmation_type,
    skip_reason,
    discovery_method: str = "",
) -> str:
    views_str = f"{views_count:,} ko'rish" if views_count else "ko'rishlar yo'q"
    url_str = post_url or "URL yo'q"
    method_str = f" [{discovery_method}]" if discovery_method else ""
    if status == "COUNTED":
        return f"✅ {url_str} — {views_str} | {confirmation_type}{method_str}"
    else:
        reason = skip_reason or status
        return f"⏭ [{status}] {url_str} — {reason}"
