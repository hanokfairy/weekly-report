import requests

SLACK_TEXT_LIMIT = 39000  # Slack incoming webhook text 한도(4만자)에 여유를 둠


def _to_slack_mrkdwn(markdown_text: str) -> str:
    """Slack mrkdwn은 굵은 글씨가 단일 별표(*)라 표준 마크다운(**)과 다름."""
    lines = []
    for line in markdown_text.splitlines():
        stripped = line.lstrip("#").strip()
        if line.startswith("#"):
            lines.append(f"*{stripped}*")
        else:
            lines.append(line.replace("**", "*"))
    return "\n".join(lines)


def send_to_slack(webhook_url: str, markdown_report: str) -> None:
    text = _to_slack_mrkdwn(markdown_report)
    chunks = [text[i : i + SLACK_TEXT_LIMIT] for i in range(0, len(text), SLACK_TEXT_LIMIT)] or [""]
    for chunk in chunks:
        resp = requests.post(webhook_url, json={"text": chunk}, timeout=10)
        resp.raise_for_status()
