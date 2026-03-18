"""Maqolalarda risk signallarini aniqlash."""
from database.models import Article

RISK_KEYWORDS: dict[str, list[str]] = {
    "economic": [
        "инфляция", "кризис", "дефицит", "санкции", "девальвация",
        "inflyatsiya", "krizis", "defitsit", "devalvatsiya", "tushish",
    ],
    "regulatory": [
        "запрет", "ограничение", "штраф", "проверка",
        "taqiq", "cheklov", "jarima", "tekshiruv",
    ],
    "political": [
        "отставка", "конфликт", "протест",
        "iste'fo", "qarama-qarshi", "norozilik",
    ],
    "sector": [
        "банкротство", "закрытие", "кризис",
        "bankrotlik", "yopilish", "inqiroz",
    ],
}


def calculate_risk_score(article: Article) -> float:
    """Maqola uchun risk score (0-100) hisoblash."""
    text = f"{article.title} {article.content}".lower()
    total_hits = 0

    for category, keywords in RISK_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        total_hits += hits

    # Har bir hit 10 ball, maksimal 100
    score = min(total_hits * 10, 100)
    return float(score)
