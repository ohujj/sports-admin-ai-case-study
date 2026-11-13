from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ComparisonQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    program_code: str = Field(pattern='^[A-Z0-9-]{1,32}$')
    base_month: str = Field(pattern='^[0-9]{4}-[0-9]{2}$', examples=['2026-10'])
    target_month: str = Field(pattern='^[0-9]{4}-[0-9]{2}$', examples=['2026-11'])

    @model_validator(mode='after')
    def validate_months(self):
        try:
            base = date.fromisoformat(f'{self.base_month}-01')
            target = date.fromisoformat(f'{self.target_month}-01')
        except ValueError:
            raise ValueError('유효한 YYYY-MM 형식의 월을 입력하세요.') from None
        if (target.year - base.year) * 12 + target.month - base.month != 1:
            raise ValueError('비교 월은 기준 월의 바로 다음 달이어야 합니다.')
        return self

class MembersQuery(ComparisonQuery):
    status: Literal['all', 'retained', 'not_retained'] = 'all'
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

class Program(BaseModel):
    program_code: str
    program_name: str

class RetentionSummary(BaseModel):
    source: Literal['mock'] = 'mock'
    dataset_as_of: datetime
    is_provisional: bool
    program: Program
    base_month: str
    target_month: str
    base_count: int
    retained_count: int
    not_retained_count: int
    new_registration_count: int | None
    continuous_registration_count: int | None
    retention_rate: float | None
    definition: str = '전월 유효 등록 회원 중 다음 달에도 동일 강습에 유효 등록이 있는 회원 비율'

class RetentionMember(BaseModel):
    member_id: str
    display_name: str
    status: Literal['retained', 'not_retained']
    registration_type: Literal['new_registration', 'continuous_registration'] | None

class RetentionMembers(BaseModel):
    source: Literal['mock'] = 'mock'
    dataset_as_of: datetime
    is_provisional: bool
    program: Program
    base_month: str
    target_month: str
    status: Literal['all', 'retained', 'not_retained']
    total: int
    offset: int
    limit: int
    members: list[RetentionMember]

class TrendQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    base_month: str = Field(pattern='^[0-9]{4}-[0-9]{2}$')
    target_month: str = Field(pattern='^[0-9]{4}-[0-9]{2}$')
    program_codes: list[str] = Field(default_factory=list)
    min_drop_pp: float = Field(default=0, ge=0, le=100)
    search_keyword: str = Field(default='', max_length=50)

    @model_validator(mode='after')
    def validate_scope(self):
        ComparisonQuery(program_code='VALID', base_month=self.base_month, target_month=self.target_month)
        if self.base_month == '0001-01':
            raise ValueError('직전 월을 계산할 수 없습니다.')
        if len(set(self.program_codes)) != len(self.program_codes):
            raise ValueError('강습 코드는 중복 없이 지정하세요.')
        for code in self.program_codes:
            ComparisonQuery(program_code=code, base_month=self.base_month, target_month=self.target_month)
        if self.program_codes and self.search_keyword:
            raise ValueError('강습 코드 지정과 검색어는 함께 사용할 수 없습니다.')
        return self

class TrendItem(BaseModel):
    program: Program
    previous_base_count: int
    previous_retained_count: int
    current_base_count: int
    current_retained_count: int
    previous_rate: float | None
    current_rate: float | None
    change_pp: float | None
    status: Literal['declined', 'increased', 'unchanged', 'not_calculable']
    meets_threshold: bool

class RetentionTrend(BaseModel):
    source: Literal['mock']
    dataset_as_of: datetime
    is_provisional: bool
    previous_base_month: str
    base_month: str
    target_month: str
    min_drop_pp: float
    scope: str
    analyzed_count: int
    declined_count: int
    not_calculable_count: int
    definition: str
    items: list[TrendItem]
