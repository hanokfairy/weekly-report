import requests

BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"


def check_keyword_rank(
    keyword: str,
    target_blog_id: str,
    client_id: str,
    client_secret: str,
    max_rank: int = 30,
) -> list[int]:
    """target_blog_id가 노출된 순위 목록을 반환 (여러 글이 걸리면 여러 순위)."""
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    marker = f"blog.naver.com/{target_blog_id}/"
    ranks: list[int] = []
    start = 1
    while start <= max_rank:
        display = min(100, max_rank - start + 1)
        params = {"query": keyword, "display": display, "start": start, "sort": "sim"}
        resp = requests.get(BLOG_SEARCH_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            break
        for i, item in enumerate(items):
            link = item.get("link", "") + item.get("bloggerlink", "")
            if marker in link:
                ranks.append(start + i)
        start += len(items)
    return ranks


def check_all_keywords(
    keywords: list[str],
    target_blog_id: str,
    client_id: str,
    client_secret: str,
    max_rank: int = 30,
) -> dict[str, list[int]]:
    return {
        kw: check_keyword_rank(kw, target_blog_id, client_id, client_secret, max_rank)
        for kw in keywords
    }
