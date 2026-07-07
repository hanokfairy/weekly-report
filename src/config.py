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


def load_clients_raw() -> dict:
    with open(CONFIG_DIR / "clients.json", encoding="utf-8") as f:
        return json.load(f)


def save_clients(data: dict) -> None:
    with open(CONFIG_DIR / "clients.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_manual_status(client_id: str) -> dict:
    with open(CONFIG_DIR / "manual_status.json", encoding="utf-8") as f:
        data = json.load(f)
    return data["clients"].get(client_id, {})


def load_manual_status_all() -> dict:
    with open(CONFIG_DIR / "manual_status.json", encoding="utf-8") as f:
        return json.load(f)


def save_manual_status(data: dict) -> None:
    with open(CONFIG_DIR / "manual_status.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"환경 변수 {name}가 설정되지 않았습니다 (.env 확인)")
    return value
