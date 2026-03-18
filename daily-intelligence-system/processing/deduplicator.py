"""Dublikat maqolalarni aniqlash — TF-IDF + cosine similarity."""
from datetime import datetime, timedelta
from typing import Optional
import redis.asyncio as aioredis
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from loguru import logger
from backend.core.config import settings


SIMILARITY_THRESHOLD = 0.85
CACHE_TTL = 86400  # 24 soat


class Deduplicator:
    """TF-IDF asosida dublikat maqolalarni aniqlash."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        if not self._redis:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def is_duplicate_url(self, url: str) -> bool:
        """URL bo'yicha tezkor dublikat tekshirish."""
        try:
            r = await self._get_redis()
            key = f"url:{url}"
            exists = await r.exists(key)
            if not exists:
                await r.setex(key, CACHE_TTL, "1")
            return bool(exists)
        except Exception as e:
            logger.warning(f"Redis error in duplicate check: {e}")
            return False

    def is_duplicate_content(
        self, new_text: str, existing_texts: list[str]
    ) -> tuple[bool, Optional[int]]:
        """Mazmun bo'yicha dublikat aniqlash (TF-IDF + cosine similarity)."""
        if not existing_texts:
            return False, None

        try:
            all_texts = existing_texts + [new_text]
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            new_vec = tfidf_matrix[-1]
            existing_matrix = tfidf_matrix[:-1]

            similarities = cosine_similarity(new_vec, existing_matrix).flatten()
            max_idx = int(np.argmax(similarities))
            max_sim = similarities[max_idx]

            if max_sim >= SIMILARITY_THRESHOLD:
                return True, max_idx
            return False, None

        except Exception as e:
            logger.warning(f"TF-IDF similarity error: {e}")
            return False, None
