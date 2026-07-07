from datetime import date

from src.config import load_manual_status
from src.ga4_client import fetch_ga4_summary
from src.naver_rank import check_all_keywords
from src.news_search import search_medical_issues
from src.report_builder import build_client_report
from src.rss_collector import get_last_week_posts
from src.slack_notifier import send_report_file

DEFAULT_ALERT_THRESHOLD_PCT = 15


def run_for_client(
    client: dict,
    naver_id: str,
    naver_secret: str,
    ga4_credentials_path: str,
    slack_bot_token: str,
) -> str:
    """클라이언트 한 곳의 주간보고를 생성하고 Slack에 파일로 전송한 뒤, 보고서 텍스트를 반환한다."""
    print(f"[{client['name']}] GA4 데이터 수집 중...")
    ga4_summary = fetch_ga4_summary(client["ga4"]["property_id"], ga4_credentials_path)

    print(f"[{client['name']}] 네이버 키워드 순위 확인 중...")
    naver_cfg = client["naver_rank"]
    naver_ranks = check_all_keywords(
        keywords=naver_cfg["keywords"],
        target_blog_id=naver_cfg["target_blog_id"],
        client_id=naver_id,
        client_secret=naver_secret,
        max_rank=naver_cfg.get("max_rank", 30),
    )

    print(f"[{client['name']}] 블로그 RSS 수집 중...")
    rss_posts_by_blog = {
        blog["name"]: get_last_week_posts(blog["rss_url"]) for blog in client["blogs"]
    }

    manual_status = load_manual_status(client["id"])

    news_issues = []
    pct_change = ga4_summary.get("pct_change")
    threshold = client.get("alert_threshold_pct", DEFAULT_ALERT_THRESHOLD_PCT)
    if pct_change is not None and abs(pct_change) >= threshold:
        news_keywords = client.get("news_keywords") or client["naver_rank"]["keywords"][:3]
        print(f"[{client['name']}] 유입 변동 {pct_change:+.1f}% 감지, 관련 의료 이슈 검색 중...")
        news_issues = search_medical_issues(
            keywords=news_keywords,
            client_id=naver_id,
            client_secret=naver_secret,
        )

    client_report = build_client_report(
        client, ga4_summary, naver_ranks, rss_posts_by_blog, manual_status, news_issues
    )

    report_date = date.today()
    title_date = f"{report_date.month}월 {report_date.day}일"
    print(f"[{client['name']}] 슬랙 전송 중...")
    send_report_file(
        bot_token=slack_bot_token,
        channel_id=client["slack"]["channel_id"],
        title=f"[{client['name']}_{title_date} 주간보고]",
        content=client_report,
        filename=f"{client['name']}_{report_date.isoformat()}_주간보고.txt",
    )

    return client_report
