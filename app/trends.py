"""Read-only retention trend calculation; no member rows leave this service."""
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from fastapi import HTTPException
from app.models import TrendQuery, TrendItem, RetentionTrend
from app.mock_data import PROGRAMS, REGISTRATIONS, COVERED_MONTHS, DATASET_AS_OF, DEMO_ORGANIZATION

def program_catalog(search_keyword=''):
    return [p for p in PROGRAMS if search_keyword.lower() in (p.program_name + p.program_code).lower()]

def previous_month(month):
    return (date.fromisoformat(month + '-01') - timedelta(days=1)).strftime('%Y-%m')

def read_declines(query: TrendQuery):
    started = DATASET_AS_OF
    previous = previous_month(query.base_month)
    months = (previous, query.base_month, query.target_month)
    if True and any((m not in COVERED_MONTHS for m in months)):
        raise HTTPException(422, {'code': 'MOCK_PERIOD_UNAVAILABLE', 'message': '합성 추세 분석은 2026-09 → 10 → 11월을 지원합니다.'})
    if query.program_codes:
        known = {p.program_code: p for p in PROGRAMS}
        if any((code not in known for code in query.program_codes)):
            raise HTTPException(404, {'code': 'PROGRAM_NOT_FOUND', 'message': '알 수 없는 강습 코드입니다.'})
        programs = [known[code] for code in query.program_codes]
        scope = '사용자가 지정한 강습'
    else:
        programs = program_catalog(query.search_keyword)
        scope = '합성 강습 전체'
        if query.search_keyword:
            scope += ' 중 검색어에 일치하는 강습'
    rows = []
    for program in programs:
        monthly = []
        for month in months:
            first = date.fromisoformat(month + '-01')
            last = first.replace(day=monthrange(first.year, first.month)[1])
            members = {r.member_id for r in REGISTRATIONS if r.organization_id == DEMO_ORGANIZATION and r.program_code == program.program_code and r.active and r.paid and (not r.cancelled) and (r.start <= last) and (r.end >= first)}
            monthly.append(members)
        before, base, target = monthly
        old_count = len(before & base)
        new_count = len(base & target)
        old_rate = Fraction(old_count * 100, len(before)) if before else None
        new_rate = Fraction(new_count * 100, len(base)) if base else None
        change = new_rate - old_rate if old_rate is not None and new_rate is not None else None
        status = 'not_calculable' if change is None else 'declined' if change < 0 else 'increased' if change > 0 else 'unchanged'
        matches = change is not None and change < 0 and (-change >= Fraction(str(query.min_drop_pp)))
        row = TrendItem(program=program, previous_base_count=len(before), previous_retained_count=old_count, current_base_count=len(base), current_retained_count=new_count, previous_rate=round(float(old_rate), 2) if old_rate is not None else None, current_rate=round(float(new_rate), 2) if new_rate is not None else None, change_pp=round(float(change), 2) if change is not None else None, status=status, meets_threshold=matches)
        rows.append((change, row))
    rows.sort(key=lambda pair: (pair[0] is None, pair[0] or 0, pair[1].program.program_code))
    items = [row for _, row in rows]
    return RetentionTrend(source='mock', dataset_as_of=started, is_provisional=True, previous_base_month=previous, base_month=query.base_month, target_month=query.target_month, min_drop_pp=query.min_drop_pp, scope=scope, analyzed_count=len(items), declined_count=sum((r.meets_threshold for r in items)), not_calculable_count=sum((r.change_pp is None for r in items)), definition='유지율=(기준 월·다음 달 공통 회원수/기준 월 회원수)×100. 변화=%p(현재 유지율−직전 유지율). 반올림 전 값으로 하락 판정. 분모0은 산출 불가. 합성 데이터이며 실제 운영 성과나 하락 원인을 뜻하지 않음.' + ' 합성 데이터.', items=items)

def format_trend(result):
    return f'{result.scope} {result.analyzed_count}개 분석: {result.previous_base_month}→{result.base_month} 대비 {result.base_month}→{result.target_month} 유지율이 하락 조건(실제 하락, 최소 {result.min_drop_pp:g}%p)에 해당하는 강습은 {result.declined_count}개입니다. 산출 불가 {result.not_calculable_count}개. 변화와 기준 인원은 아래 표에서 확인하세요. %가 아닌 %p 변화이며 현재 상태의 잠정 결과입니다. 하락 원인은 이 자료만으로 판단할 수 없습니다.'
