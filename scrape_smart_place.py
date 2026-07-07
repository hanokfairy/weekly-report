import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import env, load_clients
from src.ga4_client import last_full_week
from src.slack_notifier import send_text_message
from src.smart_place_scraper import (
    SmartPlaceLoginRequired,
    VpnNotConnected,
    check_vpn_connected,
    fetch_smart_place_stats,
)

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = ROOT_DIR / "config"
CREDENTIALS_PATH = CONFIG_DIR / "smart_place_credentials.json"
MANUAL_STATUS_PATH = CONFIG_DIR / "manual_status.json"


def load_credentials() -> dict:
    if not CREDENTIALS_PATH.exists():
        return {}
    with open(CREDENTIALS_PATH, encoding="utf-8") as f:
        return json.load(f)


def run(interactive: bool) -> None:
    credentials = load_credentials()
    if not credentials:
        print(f"{CREDENTIALS_PATH}가 없거나 비어 있습니다. 등록된 클라이언트가 없어 종료합니다.")
        return

    clients_by_id = {c["id"]: c for c in load_clients()}

    try:
        check_vpn_connected(os.getenv("EXPECTED_VPN_IP_PREFIX") or None)
    except VpnNotConnected as e:
        print(f"중단: {e}")
        try:
            slack_bot_token = env("SLACK_BOT_TOKEN")
        except RuntimeError:
            slack_bot_token = None
        if slack_bot_token:
            for client_id in credentials:
                client = clients_by_id.get(client_id)
                if client:
                    send_text_message(
                        slack_bot_token,
                        client["slack"]["channel_id"],
                        f"[{client['name']}] 스마트플레이스 자동 수집 중단 — ezVPN 연결 확인이 필요합니다.\n사유: {e}",
                    )
        return

    with open(MANUAL_STATUS_PATH, encoding="utf-8") as f:
        manual_status = json.load(f)

    start, end = last_full_week()
    period = f"{start.month}/{start.day} ~ {end.month}/{end.day}"

    changed = False
    failures = []

    for client_id, creds in credentials.items():
        print(f"[{client_id}] 스마트플레이스 통계 수집 중...")
        try:
            stats = fetch_smart_place_stats(
                client_id=client_id,
                naver_id=creds["naver_id"],
                naver_pw=creds["naver_pw"],
                stats_url=creds["stats_url"],
                interactive=interactive,
            )
        except SmartPlaceLoginRequired as e:
            print(f"[{client_id}] {e}")
            failures.append((client_id, str(e)))
            continue
        except Exception as e:
            print(f"[{client_id}] 수집 실패: {e}")
            failures.append((client_id, str(e)))
            continue

        prev_entry = manual_status["clients"].get(client_id, {}).get("smart_place", {})
        manual_status["clients"].setdefault(client_id, {})["smart_place"] = {
            "period": period,
            "visits": stats["visits"],
            "visits_prev_week": prev_entry.get("visits", stats["visits"]),
            "reservations": stats["reservations"],
            "reviews": stats["reviews"],
        }
        changed = True
        print(f"[{client_id}] 완료: 방문 {stats['visits']} / 예약 {stats['reservations']} / 리뷰 {stats['reviews']}")

    if changed:
        with open(MANUAL_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(manual_status, f, ensure_ascii=False, indent=2)
            f.write("\n")
        subprocess.run(["git", "add", str(MANUAL_STATUS_PATH)], cwd=ROOT_DIR, check=True)
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=ROOT_DIR
        )
        if diff.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", f"chore: 스마트플레이스 자동 수집 ({period})"],
                cwd=ROOT_DIR,
                check=True,
            )
            subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=ROOT_DIR, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=ROOT_DIR, check=True)
            print("변경사항을 GitHub에 push했습니다.")

    if failures:
        try:
            slack_bot_token = env("SLACK_BOT_TOKEN")
        except RuntimeError:
            slack_bot_token = None
        for client_id, message in failures:
            print(f"[{client_id}] 실패로 인해 이전 수치를 그대로 유지합니다: {message}")
            client = clients_by_id.get(client_id)
            if slack_bot_token and client:
                send_text_message(
                    slack_bot_token,
                    client["slack"]["channel_id"],
                    f"[{client['name']}] 스마트플레이스 자동 수집 실패 — 수동 확인이 필요합니다.\n사유: {message}",
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="브라우저 창을 띄워 최초 로그인/본인인증을 직접 진행",
    )
    args = parser.parse_args()
    run(interactive=args.interactive)
