"""직접 작성한 합성 데이터. 회사 소스·DB·실제 회원정보를 사용하지 않는다."""
from dataclasses import dataclass
from datetime import date, datetime
from app.models import Program
DEMO_ORGANIZATION = 'DEMO-CENTER-01'
DATASET_AS_OF = datetime.fromisoformat('2026-11-12T09:00:00+09:00')
COVERED_MONTHS = ('2026-09', '2026-10', '2026-11')
PROGRAMS = (Program(program_code='DEMO-SWIM-A', program_name='A강습 · 가상 수영 기초'), Program(program_code='DEMO-SWIM-B', program_name='B강습 · 전월 등록 0명 예제'), Program(program_code='DEMO-SWIM-C', program_name='C강습 · 유지율 동일'), Program(program_code='DEMO-SWIM-D', program_name='D강습 · 유지율 하락'), Program(program_code='DEMO-SWIM-E', program_name='E강습 · 유지율 상승'))

@dataclass(frozen=True)
class Registration:
    registration_id: str
    member_id: str
    start: date
    end: date
    program_code: str = 'DEMO-SWIM-A'
    organization_id: str = DEMO_ORGANIZATION
    paid: bool = True
    active: bool = True
    cancelled: bool = False

def make_registration(key, member, start, end, **flags):
    return Registration(key, member, date.fromisoformat(start), date.fromisoformat(end), **flags)
REGISTRATIONS = tuple((make_registration(f'oct-{i}', f'M{i:03}', '2026-10-01', '2026-10-31') for i in (1, 2, 3, 4, 7, 8))) + tuple((make_registration(f'nov-{i}', f'M{i:03}', '2026-11-01', '2026-11-30') for i in (1, 2, 3, 4, 9, 10, 11, 12))) + (make_registration('oct-3-duplicate', 'M003', '2026-10-01', '2026-10-31'), make_registration('long-5', 'M005', '2026-10-01', '2026-12-31'), make_registration('long-6', 'M006', '2026-10-15', '2026-11-15'), make_registration('nov-7-cancelled', 'M007', '2026-11-01', '2026-11-30', cancelled=True), make_registration('nov-8-unpaid', 'M008', '2026-11-01', '2026-11-30', paid=False), make_registration('oct-11-inactive', 'M011', '2026-10-01', '2026-10-31', active=False), make_registration('oct-12-unpaid', 'M012', '2026-10-01', '2026-10-31', paid=False), make_registration('other-center-7', 'M007', '2026-11-01', '2026-11-30', organization_id='DEMO-CENTER-02'), make_registration('other-program-8', 'M008', '2026-11-01', '2026-11-30', program_code='DEMO-SWIM-B'))
REGISTRATIONS += tuple((make_registration(f'sep-a-{i}', f'M{i:03}', '2026-09-01', '2026-09-30') for i in (*range(1, 9), 13, 14)))
REGISTRATIONS += tuple((make_registration(f'sep-b-{i}', f'B{i}', '2026-09-01', '2026-09-30', program_code='DEMO-SWIM-B') for i in range(2)))
for code, counts in (('C', (4, 4, 4)), ('D', (4, 4, 2)), ('E', (4, 2, 2))):
    for month, count in zip((9, 10, 11), counts):
        end = 30 if month in (9, 11) else 31
        REGISTRATIONS += tuple((make_registration(f'{code}-{month}-{i}', f'{code}{i}', f'2026-{month:02}-01', f'2026-{month:02}-{end}', program_code=f'DEMO-SWIM-{code}') for i in range(count)))
