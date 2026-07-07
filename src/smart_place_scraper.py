import re
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

LOGIN_URL = "https://nid.naver.com/nidlogin.login"
SESSION_DIR = Path(__file__).resolve().parent.parent / "config" / ".smart_place_sessions"

# 네이버 스마트플레이스 통계 화면에 표시되는 라벨 문구.
# 네이버가 화면 구성을 바꾸면 이 라벨 문자열도 함께 바뀌었는지 확인이 필요합니다.
VISITS_LABEL = "방문"
RESERVATIONS_LABEL = "예약"
REVIEWS_LABEL = "리뷰"


class SmartPlaceLoginRequired(RuntimeError):
    """세션이 만료되어 사람이 직접 로그인/본인인증을 해야 하는 경우."""


def _session_path(client_id: str) -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR / f"{client_id}.json"


def _extract_number_near_label(page: Page, label: str) -> int | None:
    """라벨 문구를 포함한 요소를 찾아, 그 부모 텍스트에서 첫 숫자를 뽑아낸다."""
    locator = page.get_by_text(label, exact=False)
    count = locator.count()
    for i in range(count):
        element = locator.nth(i)
        try:
            text = element.locator("xpath=..").inner_text(timeout=2000)
        except Exception:
            continue
        match = re.search(r"[\d,]+", text.replace(label, ""))
        if match:
            return int(match.group().replace(",", ""))
    return None


def _login(page: Page, naver_id: str, naver_pw: str) -> None:
    page.goto(LOGIN_URL)
    # 네이버 로그인 폼은 자동입력 방지를 위해 keyboard 이벤트를 감시하므로,
    # 자바스크립트로 값을 직접 주입하는 방식으로 우회한다 (자동화 도구들의 일반적인 우회 방법).
    page.evaluate(
        """([id, pw]) => {
            document.getElementById('id').value = id;
            document.getElementById('pw').value = pw;
        }""",
        [naver_id, naver_pw],
    )
    page.click("#log\\.login")
    page.wait_for_load_state("networkidle")

    if "nidlogin" in page.url or "deviceConfirm" in page.url:
        raise SmartPlaceLoginRequired(
            "네이버가 추가 본인인증을 요구합니다. --interactive 옵션으로 한 번 직접 로그인해야 합니다."
        )


def fetch_smart_place_stats(
    client_id: str,
    naver_id: str,
    naver_pw: str,
    stats_url: str,
    interactive: bool = False,
) -> dict:
    """스마트플레이스 통계 페이지에서 방문/예약/리뷰 수치를 긁어온다.

    interactive=True인 경우 브라우저 창을 띄워 사람이 직접 로그인/본인인증을 완료할 시간을 준다
    (최초 1회, 혹은 세션 만료 시 필요).
    """
    session_path = _session_path(client_id)
    storage_state = str(session_path) if session_path.exists() else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not interactive)
        context = browser.new_context(storage_state=storage_state)
        page = context.new_page()

        page.goto(stats_url)
        page.wait_for_load_state("networkidle")

        if "nid.naver.com" in page.url:
            if interactive:
                _login(page, naver_id, naver_pw)
                print(f"[{client_id}] 로그인/본인인증을 마쳤다면 통계 페이지가 뜰 때까지 기다립니다...")
                page.wait_for_url(lambda url: "nid.naver.com" not in url, timeout=120_000)
                page.goto(stats_url)
                page.wait_for_load_state("networkidle")
            else:
                context.close()
                browser.close()
                raise SmartPlaceLoginRequired(
                    f"[{client_id}] 저장된 로그인 세션이 없거나 만료되었습니다. "
                    "python3 scrape_smart_place.py --interactive 로 최초 1회 수동 로그인이 필요합니다."
                )

        visits = _extract_number_near_label(page, VISITS_LABEL)
        reservations = _extract_number_near_label(page, RESERVATIONS_LABEL)
        reviews = _extract_number_near_label(page, REVIEWS_LABEL)

        context.storage_state(path=str(session_path))
        context.close()
        browser.close()

    if visits is None:
        raise RuntimeError(
            f"[{client_id}] 방문자 수를 찾지 못했습니다. 네이버 페이지 구조가 바뀌었을 수 있어 "
            "src/smart_place_scraper.py의 라벨 문자열 확인이 필요합니다."
        )

    return {
        "visits": visits,
        "reservations": reservations or 0,
        "reviews": reviews or 0,
    }
