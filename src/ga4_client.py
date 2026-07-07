from datetime import date, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)


def last_full_week() -> tuple[date, date]:
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday


def previous_week(start: date, end: date) -> tuple[date, date]:
    return start - timedelta(days=7), end - timedelta(days=7)


def fetch_ga4_summary(property_id: str, credentials_path: str) -> dict:
    client = BetaAnalyticsDataClient.from_service_account_file(credentials_path)
    start, end = last_full_week()
    prev_start, prev_end = previous_week(start, end)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
    )
    response = client.run_report(request)

    channels = []
    total_sessions = 0
    total_users = 0
    for row in response.rows:
        sessions = int(row.metric_values[0].value)
        users = int(row.metric_values[1].value)
        channels.append(
            {"channel": row.dimension_values[0].value, "sessions": sessions, "users": users}
        )
        total_sessions += sessions
        total_users += users

    channels.sort(key=lambda c: c["sessions"], reverse=True)

    # 전주 대비 유입 변동율 계산용 (채널 구분 없이 총 세션만 조회)
    prev_request = RunReportRequest(
        property=f"properties/{property_id}",
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=prev_start.isoformat(), end_date=prev_end.isoformat())],
    )
    prev_response = client.run_report(prev_request)
    prev_total_sessions = sum(int(row.metric_values[0].value) for row in prev_response.rows)

    pct_change = None
    if prev_total_sessions:
        pct_change = round((total_sessions - prev_total_sessions) / prev_total_sessions * 100, 1)

    return {
        "period": (start.isoformat(), end.isoformat()),
        "prev_period": (prev_start.isoformat(), prev_end.isoformat()),
        "total_sessions": total_sessions,
        "total_users": total_users,
        "prev_total_sessions": prev_total_sessions,
        "pct_change": pct_change,
        "channels": channels,
    }
