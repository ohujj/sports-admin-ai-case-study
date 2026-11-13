from calendar import monthrange
from datetime import date
from fastapi import HTTPException
from app.mock_data import COVERED_MONTHS, DATASET_AS_OF, DEMO_ORGANIZATION, PROGRAMS, REGISTRATIONS
from app.models import ComparisonQuery, MembersQuery, RetentionMember, RetentionMembers, RetentionSummary

def compare_registrations(query: ComparisonQuery):
    program = next((p for p in PROGRAMS if p.program_code == query.program_code), None)
    if program is None:
        raise HTTPException(404, {'code': 'PROGRAM_NOT_FOUND', 'message': '가상 강습을 찾을 수 없습니다.'})
    if query.base_month not in COVERED_MONTHS or query.target_month not in COVERED_MONTHS:
        raise HTTPException(422, {'code': 'MOCK_PERIOD_UNAVAILABLE', 'message': 'Mock은 2026-09 → 10월 또는 10 → 11월 비교를 제공합니다.'})
    monthly = []
    for month in (query.base_month, query.target_month):
        first = date.fromisoformat(f'{month}-01')
        last = first.replace(day=monthrange(first.year, first.month)[1])
        member_records = {}
        for row in REGISTRATIONS:
            if row.organization_id == DEMO_ORGANIZATION and row.program_code == query.program_code and row.paid and row.active and (not row.cancelled) and (row.start <= last) and (row.end >= first):
                member_records.setdefault(row.member_id, set()).add(row.registration_id)
        monthly.append(member_records)
    base, target = monthly
    members = []
    for member_id in sorted(base):
        registration_type = None
        if member_id in target:
            registration_type = 'new_registration' if target[member_id] - base[member_id] else 'continuous_registration'
        members.append(RetentionMember(member_id=member_id, display_name=f'가상회원 {member_id[1:]}', status='retained' if member_id in target else 'not_retained', registration_type=registration_type))
    return (program, members)

def read_retention_summary(query: ComparisonQuery) -> RetentionSummary:
    program, members = compare_registrations(query)
    retained = sum((m.status == 'retained' for m in members))
    return RetentionSummary(dataset_as_of=DATASET_AS_OF, is_provisional=is_provisional(query.target_month), program=program, base_month=query.base_month, target_month=query.target_month, base_count=len(members), retained_count=retained, not_retained_count=len(members) - retained, new_registration_count=sum((m.registration_type == 'new_registration' for m in members)), continuous_registration_count=sum((m.registration_type == 'continuous_registration' for m in members)), retention_rate=round(retained / len(members) * 100, 2) if members else None)

def read_retention_members(query: MembersQuery) -> RetentionMembers:
    program, members = compare_registrations(query)
    filtered = [m for m in members if query.status == 'all' or m.status == query.status]
    return RetentionMembers(dataset_as_of=DATASET_AS_OF, is_provisional=is_provisional(query.target_month), program=program, base_month=query.base_month, target_month=query.target_month, status=query.status, total=len(filtered), offset=query.offset, limit=query.limit, members=filtered[query.offset:query.offset + query.limit])

def is_provisional(month: str) -> bool:
    first = date.fromisoformat(f'{month}-01')
    return DATASET_AS_OF.date() <= first.replace(day=monthrange(first.year, first.month)[1])
