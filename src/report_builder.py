def build_client_report(
    client: dict,
    ga4_summary: dict,
    naver_ranks: dict[str, list[int]],
    rss_posts_by_blog: dict[str, list[dict]],
    manual_status: dict,
    news_issues: list[dict] | None = None,
) -> str:
    name = client["name"]
    lines = [f"# {name} 주간 보고", ""]

    # 1. 채널별 진행 현황 (수동 입력값 기반)
    lines.append("## 1. 채널별 진행 현황")
    channels = manual_status.get("channels", {})
    if "blog" in channels:
        b = channels["blog"]
        lines.append(f"- 블로그: {b['target']}건 중 {b['done']}건 진행 완료")
    if "cafe" in channels:
        c = channels["cafe"]
        note = f" ({c['note']})" if c.get("note") else ""
        lines.append(f"- 카페 침투: {c['target']}세트 중 {c['done']}건 진행 대기중{note}")
    if "receipt_review" in channels:
        r = channels["receipt_review"]
        note = r.get("note", "지속 진행 중")
        lines.append(f"- 영수증 리뷰: {r['target']}건 목표 {note}")
    lines.append("")

    # 2. 주요 관리 키워드 노출 현황 (네이버 검색 API)
    lines.append("## 2. 주요 관리 키워드 노출 현황")
    for keyword, ranks in naver_ranks.items():
        rank_str = ", ".join(f"{r}위" for r in sorted(ranks)) if ranks else "순위권 밖"
        lines.append(f"- {keyword}: {rank_str}")
    lines.append("")

    # 3. 스마트 플레이스 / GA4 유입 통계
    sp = manual_status.get("smart_place")
    if sp:
        lines.append(f"## 3. 스마트 플레이스 주간 통계 ({sp['period']} 기준)")
        diff = sp["visits"] - sp["visits_prev_week"]
        trend = "증가" if diff > 0 else "감소" if diff < 0 else "동일"
        lines.append(
            f"- 총 유입수: {sp['visits']:,}회 (전주 {sp['visits_prev_week']:,}회 대비 {trend})"
        )
        lines.append(f"- 예약/주문 신청: {sp['reservations']}건")
        lines.append(f"- 리뷰 등록: {sp['reviews']}건")
        lines.append("")

    lines.append("## 4. GA4 웹사이트 유입 현황")
    start, end = ga4_summary["period"]
    lines.append(f"- 기간: {start} ~ {end}")
    lines.append(f"- 총 세션: {ga4_summary['total_sessions']:,} / 총 사용자: {ga4_summary['total_users']:,}")
    pct_change = ga4_summary.get("pct_change")
    if pct_change is not None:
        trend = "증가" if pct_change > 0 else "감소" if pct_change < 0 else "동일"
        lines.append(
            f"- 전주 대비: {pct_change:+.1f}% ({trend}, 전주 세션 {ga4_summary['prev_total_sessions']:,})"
        )
    lines.append("- 유입경로별:")
    for ch in ga4_summary["channels"]:
        lines.append(f"  - {ch['channel']}: 세션 {ch['sessions']:,} / 사용자 {ch['users']:,}")
    lines.append("")

    lines.append("## 5. 블로그 신규 발행 글 (지난주)")
    for blog_name, posts in rss_posts_by_blog.items():
        lines.append(f"- {blog_name} ({len(posts)}건)")
        for post in posts:
            lines.append(f"  - [{post['title']}]({post['link']})")
    lines.append("")

    if news_issues:
        lines.append("## 6. 유입 변동 분석 참고 자료 (자동 수집)")
        lines.append(
            f"- 유입이 크게 변동하여({pct_change:+.1f}%) 관련 가능성이 있는 최근 의료계 이슈를 자동 검색했습니다. "
            "아래는 참고용 후보이며 실제 원인 여부는 확인이 필요합니다."
        )
        for issue in news_issues:
            lines.append(f"  - [{issue['pub_date']}] [{issue['title']}]({issue['link']}) (검색어: {issue['keyword']})")
        lines.append("")

    return "\n".join(lines)


def build_full_report(client_reports: list[str], report_date: str) -> str:
    header = f"# 주간 보고 ({report_date})\n\n"
    return header + "\n---\n\n".join(client_reports)
