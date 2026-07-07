import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

NEWS_SEARCH_URL = "https://openapi.naver.com/v1/search/news.json"

_TAG_RE = re.compile(r"<.*?>")


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text)


def search_medical_issues(
    keywords: list[str],
    client_id: str,
    client_secret: str,
    days: int = 14,
    display: int = 5,
) -> list[dict]:
    """최근 N일 이내 뉴스 중 keywords와 관련된 기사를 검색해 유입 변동의 참고 원인 후보로 제공."""
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    seen_links: set[str] = set()
    results: list[dict] = []
    for keyword in keywords:
        params = {"query": keyword, "display": display, "sort": "date"}
        resp = requests.get(NEWS_SEARCH_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        for item in resp.json().get("items", []):
            link = item.get("originallink") or item.get("link", "")
            if not link or link in seen_links:
                continue
            try:
                pub_date = parsedate_to_datetime(item["pubDate"])
            except (KeyError, TypeError, ValueError):
                continue
            if pub_date < cutoff:
                continue
            seen_links.add(link)
            results.append(
                {
                    "title": _strip_tags(item.get("title", "")),
                    "link": link,
                    "pub_date": pub_date.date().isoformat(),
                    "keyword": keyword,
                }
            )

    results.sort(key=lambda r: r["pub_date"], reverse=True)
    return results
