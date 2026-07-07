import json
import os
import subprocess
import sys
from functools import wraps
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from src.config import (
    ROOT_DIR,
    env,
    load_clients_raw,
    load_manual_status_all,
    save_clients,
    save_manual_status,
)
from src.pipeline import run_for_client

MAX_BLOG_SLOTS = 5

ADMIN_DIR = Path(__file__).resolve().parent
USERS_PATH = ADMIN_DIR / "users.json"
REPORTS_DIR = ROOT_DIR / "reports"

app = Flask(__name__)
app.secret_key = os.urandom(24)


def load_users() -> dict:
    if not USERS_PATH.exists():
        return {}
    with open(USERS_PATH, encoding="utf-8") as f:
        return json.load(f)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def git_commit_and_push(paths: list[Path], message: str) -> None:
    subprocess.run(["git", "add", *[str(p) for p in paths]], cwd=ROOT_DIR, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT_DIR)
    if diff.returncode == 0:
        return  # 변경 없음
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT_DIR, check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=ROOT_DIR, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT_DIR, check=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        password_hash = users.get(username)
        if password_hash and check_password_hash(password_hash, password):
            session["user"] = username
            return redirect(url_for("dashboard"))
        flash("아이디 또는 비밀번호가 올바르지 않습니다.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    clients = load_clients_raw()["clients"]
    manual_status = load_manual_status_all()["clients"]
    for client in clients:
        client["_status"] = manual_status.get(client["id"], {})
    return render_template("dashboard.html", clients=clients)


def _pad_blog_slots(blogs: list[dict]) -> list[dict]:
    empty = {"name": "", "rss_url": "", "blog_id": "", "keywords": [], "max_rank": 30}
    slots = [dict(empty, **b) for b in blogs[:MAX_BLOG_SLOTS]]
    while len(slots) < MAX_BLOG_SLOTS:
        slots.append(dict(empty))
    return slots


@app.route("/clients/new", methods=["GET", "POST"])
@login_required
def client_new():
    if request.method == "POST":
        data = load_clients_raw()
        new_client = _client_from_form(request.form)
        if any(c["id"] == new_client["id"] for c in data["clients"]):
            flash(f"이미 존재하는 id입니다: {new_client['id']}")
            return render_template(
                "client_form.html",
                client=new_client,
                is_new=True,
                blog_slots=_pad_blog_slots(new_client["blogs"]),
            )
        data["clients"].append(new_client)
        save_clients(data)
        git_commit_and_push(
            [ROOT_DIR / "config" / "clients.json"], f"클라이언트 추가: {new_client['name']}"
        )
        flash(f"{new_client['name']} 추가 완료")
        return redirect(url_for("dashboard"))
    return render_template(
        "client_form.html", client=None, is_new=True, blog_slots=_pad_blog_slots([])
    )


@app.route("/clients/<client_id>/edit", methods=["GET", "POST"])
@login_required
def client_edit(client_id):
    data = load_clients_raw()
    existing = next((c for c in data["clients"] if c["id"] == client_id), None)
    if existing is None:
        flash("존재하지 않는 클라이언트입니다.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        updated = _client_from_form(request.form, fixed_id=client_id)
        data["clients"] = [updated if c["id"] == client_id else c for c in data["clients"]]
        save_clients(data)
        git_commit_and_push(
            [ROOT_DIR / "config" / "clients.json"], f"클라이언트 수정: {updated['name']}"
        )
        flash(f"{updated['name']} 저장 완료")
        return redirect(url_for("dashboard"))

    return render_template(
        "client_form.html",
        client=existing,
        is_new=False,
        blog_slots=_pad_blog_slots(existing["blogs"]),
    )


def _blogs_from_form(form) -> list[dict]:
    blogs = []
    for i in range(MAX_BLOG_SLOTS):
        name = form.get(f"blog_name_{i}", "").strip()
        rss_url = form.get(f"blog_rss_{i}", "").strip()
        if not name or not rss_url:
            continue  # 빈 슬롯은 건너뜀
        keywords = [k.strip() for k in form.get(f"blog_keywords_{i}", "").split(",") if k.strip()]
        blogs.append(
            {
                "name": name,
                "rss_url": rss_url,
                "blog_id": form.get(f"blog_id_{i}", "").strip(),
                "keywords": keywords,
                "max_rank": int(form.get(f"blog_max_rank_{i}") or 30),
            }
        )
    return blogs


def _client_from_form(form, fixed_id: str | None = None) -> dict:
    news_keywords = [k.strip() for k in form.get("news_keywords", "").split(",") if k.strip()]
    return {
        "id": fixed_id or form["id"].strip(),
        "name": form["name"].strip(),
        "ga4": {"property_id": form["property_id"].strip()},
        "blogs": _blogs_from_form(form),
        "alert_threshold_pct": int(form.get("alert_threshold_pct") or 15),
        "news_keywords": news_keywords,
        "slack": {
            "channel_id": form["channel_id"].strip(),
            "channel_name": form.get("channel_name", "").strip(),
        },
    }


@app.route("/clients/<client_id>/status", methods=["GET", "POST"])
@login_required
def client_status(client_id):
    all_status = load_manual_status_all()
    current = all_status["clients"].get(client_id, {})

    if request.method == "POST":
        form = request.form
        all_status["clients"][client_id] = {
            "channels": {
                "blog": {"target": int(form["blog_target"]), "done": int(form["blog_done"])},
                "cafe": {
                    "target": int(form["cafe_target"]),
                    "done": int(form["cafe_done"]),
                    "note": form.get("cafe_note", ""),
                },
                "receipt_review": {
                    "target": int(form["receipt_target"]),
                    "done": int(form["receipt_done"]),
                    "note": form.get("receipt_note", ""),
                },
            },
            "smart_place": {
                "period": form.get("sp_period", ""),
                "visits": int(form.get("sp_visits") or 0),
                "visits_prev_week": int(form.get("sp_visits_prev") or 0),
                "reservations": int(form.get("sp_reservations") or 0),
                "reviews": int(form.get("sp_reviews") or 0),
            },
        }
        save_manual_status(all_status)
        git_commit_and_push(
            [ROOT_DIR / "config" / "manual_status.json"], f"{client_id} 실적 수치 갱신"
        )
        flash("저장 완료")
        return redirect(url_for("dashboard"))

    channels = current.get("channels", {})
    smart_place = current.get("smart_place", {})
    normalized = {
        "blog": channels.get("blog", {"target": 0, "done": 0}),
        "cafe": channels.get("cafe", {"target": 0, "done": 0, "note": ""}),
        "receipt_review": channels.get("receipt_review", {"target": 0, "done": 0, "note": ""}),
        "smart_place": {
            "period": smart_place.get("period", ""),
            "visits": smart_place.get("visits", 0),
            "visits_prev_week": smart_place.get("visits_prev_week", 0),
            "reservations": smart_place.get("reservations", 0),
            "reviews": smart_place.get("reviews", 0),
        },
    }
    return render_template("status_form.html", client_id=client_id, s=normalized)


@app.route("/clients/<client_id>/reports")
@login_required
def client_reports(client_id):
    clients = load_clients_raw()["clients"]
    client = next((c for c in clients if c["id"] == client_id), None)
    if client is None:
        flash("존재하지 않는 클라이언트입니다.")
        return redirect(url_for("dashboard"))

    heading = f"# {client['name']} 주간 보고"
    reports = []
    for path in sorted(REPORTS_DIR.glob("*.md"), reverse=True):
        text = path.read_text(encoding="utf-8")
        for block in text.split("\n---\n\n"):
            idx = block.find(heading)
            if idx != -1:
                reports.append({"date": path.stem, "content": block[idx:].strip()})
                break

    return render_template("reports.html", client=client, reports=reports)


@app.route("/clients/<client_id>/run", methods=["POST"])
@login_required
def client_run(client_id):
    clients = load_clients_raw()["clients"]
    client = next((c for c in clients if c["id"] == client_id), None)
    if client is None:
        flash("존재하지 않는 클라이언트입니다.")
        return redirect(url_for("dashboard"))

    try:
        run_for_client(
            client,
            naver_id=env("NAVER_CLIENT_ID"),
            naver_secret=env("NAVER_CLIENT_SECRET"),
            ga4_credentials_path=env("GA4_CREDENTIALS_PATH"),
            slack_bot_token=env("SLACK_BOT_TOKEN"),
        )
        flash(f"{client['name']} 보고서를 생성해 Slack으로 전송했습니다.")
    except Exception as e:
        flash(f"실행 중 오류가 발생했습니다: {e}")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
