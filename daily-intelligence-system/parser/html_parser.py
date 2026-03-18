"""HTML parser — httpx + BeautifulSoup4 + newspaper3k bilan."""
import random
from datetime import datetime
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser
from loguru import logger
from parser.base_parser import BaseParser

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]


class HTMLParser(BaseParser):
    """HTML sahifalarni scraping qiluvchi parser."""

    def __init__(self, source_id: int, source_url: str, source_name: str,
                 article_selector: str = "article", language: str = "uz"):
        super().__init__(source_id, source_url, source_name)
        self.article_selector = article_selector
        self.language = language

    async def fetch(self) -> list[dict]:
        """Asosiy sahifadan maqolalar havolalarini olib, har birini parse qilish."""
        links = await self._get_article_links()
        articles = []
        for link in links[:20]:  # Eng ko'pi bilan 20 ta
            article = await self._parse_article_page(link)
            if article:
                articles.append(article)
        return articles

    async def _get_article_links(self) -> list[str]:
        """Asosiy sahifadan maqola havolalarini olish."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                response = await client.get(self.source_url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                links = []
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if href.startswith("http") and self.source_url.split("//")[1].split("/")[0] in href:
                        if href not in links:
                            links.append(href)
                return links[:30]
        except Exception as e:
            logger.error(f"[{self.source_name}] Failed to get links: {e}")
            return []

    async def _parse_article_page(self, url: str) -> Optional[dict]:
        """Bitta maqola sahifasini parse qilish."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Sarlavha
            title = ""
            for tag in ["h1", "h2"]:
                el = soup.find(tag)
                if el:
                    title = el.get_text(strip=True)
                    break

            if not title:
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""

            if not title or len(title) < 10:
                return None

            # Mazmun
            content = ""
            for selector in ["article", "main", ".content", ".article-body", "#content"]:
                el = soup.select_one(selector)
                if el:
                    content = el.get_text(separator=" ", strip=True)
                    break

            if not content:
                paragraphs = soup.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            if len(content) < 50:
                return None

            # Sana
            published_at = datetime.utcnow()
            for meta_name in ["article:published_time", "publishedDate", "datePublished"]:
                meta = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
                if meta and meta.get("content"):
                    try:
                        published_at = dateutil_parser.parse(meta["content"])
                        break
                    except Exception:
                        pass

            return self._build_article(title, url, content, published_at, self.language)

        except Exception as e:
            logger.warning(f"[{self.source_name}] Failed to parse {url}: {e}")
            return None
