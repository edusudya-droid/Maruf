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


def format_report(
    post_url: str,
    source_views: int,
    counted_posts_count: int,
    confirmed_secondary_views: int,
    total_confirmed_reach: int,
    skipped_posts_count: int,
    finished_at: str,
) -> str:
    return (
        "📊 <b>TASDIQLANGAN QAMROV HISOBOTI</b>\n\n"
        f"🔗 Manba: {post_url}\n"
        f"👁 Original ko'rishlar: {source_views:,}\n"
        f"📢 Tasdiqlangan tarqalishlar: {counted_posts_count} ta\n"
        f"➕ Ularning ko'rishlari: {confirmed_secondary_views:,}\n\n"
        f"<b>JAMI TASDIQLANGAN QAMROV: {total_confirmed_reach:,}</b>\n\n"
        f"⏭ O'tkazib yuborilganlar: {skipped_posts_count} ta\n"
        f"🕐 Hisoblash vaqti: {finished_at}\n\n"
        "<i>Faqat mavjud va tasdiqlangan ma'lumotlar asosida hisoblandi.</i>"
    )


def format_detected_post_line(
    status: str,
    post_url: str,
    views_count,
    confirmation_type,
    skip_reason,
) -> str:
    views_str = f"{views_count:,} ko'rish" if views_count else "ko'rishlar yo'q"
    url_str = post_url or "URL yo'q"
    if status == "COUNTED":
        return f"[COUNTED] {url_str} — {views_str} | {confirmation_type}"
    else:
        reason = skip_reason or status
        return f"[{status}] {url_str} — {reason}"
