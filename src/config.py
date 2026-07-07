import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"

load_dotenv(ROOT_DIR / ".env")


def load_clients() -> list[dict]:
    with open(CONFIG_DIR / "clients.json", encoding="utf-8") as f:
        return json.load(f)["clients"]


def load_manual_status(client_id: str) -> dict:
    with open(CONFIG_DIR / "manual_status.json", encoding="utf-8") as f:
        data = json.load(f)
    return data["clients"].get(client_id, {})


def env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"환경 변수 {name}가 설정되지 않았습니다 (.env 확인)")
    return value
