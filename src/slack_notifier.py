import requests

SLACK_API_BASE = "https://slack.com/api"


def _call(bot_token: str, endpoint: str, **kwargs) -> dict:
    headers = {"Authorization": f"Bearer {bot_token}"}
    resp = requests.post(f"{SLACK_API_BASE}/{endpoint}", headers=headers, timeout=15, **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API 오류 ({endpoint}): {data.get('error')}")
    return data


def send_text_message(bot_token: str, channel_id: str, text: str) -> None:
    """짧은 알림(예: 자동 수집 실패)을 파일 첨부 없이 텍스트로만 전송한다."""
    _call(bot_token, "chat.postMessage", json={"channel": channel_id, "text": text})


def send_report_file(
    bot_token: str,
    channel_id: str,
    title: str,
    content: str,
    filename: str,
) -> None:
    """주간보고 내용을 .txt 파일로 만들어 Slack 채널에 첨부 전송한다 (Slack 파일 업로드 v2 흐름)."""
    file_bytes = content.encode("utf-8")

    upload_info = _call(
        bot_token,
        "files.getUploadURLExternal",
        data={"filename": filename, "length": len(file_bytes)},
    )
    upload_url = upload_info["upload_url"]
    file_id = upload_info["file_id"]

    upload_resp = requests.post(
        upload_url,
        files={"file": (filename, file_bytes, "text/plain")},
        timeout=30,
    )
    upload_resp.raise_for_status()

    _call(
        bot_token,
        "files.completeUploadExternal",
        json={
            "files": [{"id": file_id, "title": title}],
            "channel_id": channel_id,
            "initial_comment": title,
        },
    )
