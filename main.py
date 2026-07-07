import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import env, load_clients, load_manual_status
from src.ga4_client import fetch_ga4_summary
from src.naver_rank import check_all_keywords
from src.news_search import search_medical_issues
from src.report_builder import build_client_report, build_full_report
from src.rss_collector import get_last_week_posts
from src.slack_notifier import send_report_file

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
DEFAULT_ALERT_THRESHOLD_PCT = 15


def run() -> None:
    naver_id = env("NAVER_CLIENT_ID")
    naver_secret = env("NAVER_CLIENT_SECRET")
    ga4_credentials_path = env("GA4_CREDENTIALS_PATH")
    slack_bot_token = env("SLACK_BOT_TOKEN")

    report_date = date.today()
    title_date = f"{report_date.month}월 {report_date.day}일"

    client_reports = []
    for client in load_clients():
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
        client_reports.append(client_report)

        print(f"[{client['name']}] 슬랙 전송 중...")
        title = f"[{client['name']}_{title_date} 주간보고]"
        send_report_file(
            bot_token=slack_bot_token,
            channel_id=client["slack"]["channel_id"],
            title=title,
            content=client_report,
            filename=f"{client['name']}_{report_date.isoformat()}_주간보고.txt",
        )

    full_report = build_full_report(client_reports, report_date.isoformat())

    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"{report_date.isoformat()}.md"
    report_path.write_text(full_report, encoding="utf-8")
    print(f"보고서 저장: {report_path}")
    print("완료.")


if __name__ == "__main__":
    run()
