from datetime import datetime, timedelta, timezone

import feedparser


def get_last_week_posts(rss_url: str) -> list[dict]:
    feed = feedparser.parse(rss_url)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    posts = []
    for entry in feed.entries:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if not published:
            continue
        published_dt = datetime(*published[:6], tzinfo=timezone.utc)
        if published_dt >= week_ago:
            posts.append(
                {
                    "title": entry.get("title", "(제목 없음)"),
                    "link": entry.get("link", ""),
                    "published": published_dt.isoformat(),
                }
            )
    return posts
