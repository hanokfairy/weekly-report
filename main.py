import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import env, load_clients
from src.pipeline import run_for_client
from src.report_builder import build_full_report

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def run() -> None:
    naver_id = env("NAVER_CLIENT_ID")
    naver_secret = env("NAVER_CLIENT_SECRET")
    ga4_credentials_path = env("GA4_CREDENTIALS_PATH")
    slack_bot_token = env("SLACK_BOT_TOKEN")

    client_reports = [
        run_for_client(client, naver_id, naver_secret, ga4_credentials_path, slack_bot_token)
        for client in load_clients()
    ]

    report_date = date.today().isoformat()
    full_report = build_full_report(client_reports, report_date)

    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"{report_date}.md"
    report_path.write_text(full_report, encoding="utf-8")
    print(f"보고서 저장: {report_path}")
    print("완료.")


if __name__ == "__main__":
    run()
