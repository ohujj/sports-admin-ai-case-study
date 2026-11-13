import logging
from pathlib import Path
from time import perf_counter
from typing import Annotated
from uuid import uuid4
from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.assistant import AssistantRequest, AssistantResponse, ask_assistant, connection_status
from app import trends
from app.mock_data import COVERED_MONTHS, DATASET_AS_OF, PROGRAMS
from app.models import ComparisonQuery, MembersQuery, Program, RetentionMembers, RetentionSummary, TrendQuery, RetentionTrend
from app.retention import read_retention_members, read_retention_summary
logger = logging.getLogger('uvicorn.error')
app = FastAPI(title='체육시설 관리자 AI PoC', version='0.3.0', description='합성 데이터 전용 로컬 관리자 업무 어시스턴트 데모.', redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])
static_path = Path(__file__).parent / 'static'
app.mount('/static', StaticFiles(directory=static_path), name='static')

@app.middleware('http')
async def log_request(request: Request, call_next):
    request.state.request_id = uuid4().hex
    started = perf_counter()
    response = await call_next(request)
    response.headers['X-Request-ID'] = request.state.request_id
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if request.url.path == '/' or request.url.path.startswith('/static/'):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    route = request.scope.get('route')
    path = getattr(route, 'path', 'unmatched')
    logger.info('request_id=%s method=%s route=%s status=%s elapsed_ms=%.1f', request.state.request_id, request.method, path, response.status_code, (perf_counter() - started) * 1000)
    return response

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'code': 'INVALID_ARGUMENT', 'message': '입력값을 확인하세요. 월은 YYYY-MM, 비교 월은 바로 다음 달이며 추가 인자는 허용하지 않습니다.', 'request_id': request.state.request_id, 'errors': [{'field': '.'.join((str(p) for p in e['loc'])), 'type': e['type']} for e in exc.errors()]})

@app.exception_handler(HTTPException)
async def api_error(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {'code': 'HTTP_ERROR', 'message': str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={**detail, 'request_id': request.state.request_id}, headers=exc.headers)

@app.get('/', include_in_schema=False)
def index():
    return FileResponse(static_path / 'index.html')

@app.get('/health', tags=['상태'])
def health():
    return {'status': 'ok', 'mode': 'mock-only', 'dataset_as_of': DATASET_AS_OF, 'covered_months': COVERED_MONTHS, 'llm_enabled': connection_status()['configured'], 'backend_enabled': False, 'synthetic_only': True}

@app.get('/api/programs', response_model=list[Program], tags=['가상 강습'])
def read_programs(search_keyword: str=Query(default='', max_length=50)):
    return trends.program_catalog(search_keyword)

@app.post('/api/retention/declines', response_model=RetentionTrend, tags=['재등록'])
def retention_declines(body: TrendQuery, request: Request):
    if request.headers.get('origin') != f"{request.url.scheme}://{request.headers.get('host')}":
        raise HTTPException(403, {'code': 'ORIGIN_NOT_ALLOWED', 'message': '같은 로컬 화면에서만 요청하세요.'})
    return trends.read_declines(body)

@app.get('/api/retention/summary', response_model=RetentionSummary, tags=['재등록'])
def retention_summary(query: Annotated[ComparisonQuery, Query()]):
    return read_retention_summary(query)

@app.get('/api/retention/members', response_model=RetentionMembers, tags=['재등록'])
def retention_members(query: Annotated[MembersQuery, Query()]):
    return read_retention_members(query)

@app.get('/api/assistant/status', tags=['AI 어시스턴트'])
def assistant_status():
    return connection_status()

@app.post('/api/assistant/chat', response_model=AssistantResponse, tags=['AI 어시스턴트'])
def assistant_chat(body: AssistantRequest, request: Request):
    origin = request.headers.get('origin')
    if origin and origin != f"{request.url.scheme}://{request.headers.get('host')}":
        raise HTTPException(403, {'code': 'ORIGIN_NOT_ALLOWED', 'message': '같은 로컬 화면에서만 요청할 수 있습니다.'})
    return ask_assistant(body)
