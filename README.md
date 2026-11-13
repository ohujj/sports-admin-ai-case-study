# 합성 데이터 전용 강습 업무 AI 실험

현재 버전은 업무 API·로그인 API·DB를 호출하지 않습니다. 직접 만든 합성 데이터와 가정한 업무 응답만 사용하고, 로컬 모델이 자연어를 해석해 허용 Tool을 선택합니다.

## 새 Windows PC 준비

아래 명령은 프로젝트 폴더의 PowerShell에서 실행합니다. Windows용 실행 스크립트를 제공합니다. 현재 검증된 환경은 Python3.14이며 다른 버전·OS의 동일 실행을 보증하지 않습니다. 필요한 소프트웨어를 설치할 권한과 모델 사용 조건을 먼저 확인하세요.

### 1. Python 환경

Python3.14와 Windows Python Launcher를 설치한 뒤 새 PowerShell을 엽니다. `py -3.14 --version`으로 확인합니다. Launcher가 없다면 해당 버전의 `python`으로 아래 첫 명령을 실행합니다.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -c "import fastapi, uvicorn, pydantic; print('dependencies ready')"
```

가상환경 activate는 필요하지 않습니다. 설치는 PyPI 네트워크 접근이 필요하며 스크립트가 자동 설치하지 않습니다. lock은 이 프로젝트에서 확인한 버전을 고정한 목록이며 취약점/라이선스 감사 결과가 아닙니다.

### 2. 로컬 Ollama와 모델

[Ollama Windows 공식 안내](https://docs.ollama.com/windows)에 따라 설치하고 PowerShell을 다시 엽니다. 표준 설치는 사용자 PATH에 명령을 추가하고 로컬 서버를 실행합니다. [모델 페이지](https://ollama.com/library/qwen3:4b-instruct)를 확인한 뒤:

```powershell
ollama --version
ollama pull qwen3:4b-instruct
```

모델 다운로드는 인터넷과 저장 공간을 사용하지만 이후 이 앱의 추론은 로컬 모델로만 수행합니다. 모델 태그는 바뀔 수 있으므로 비교 실험에는 모델 digest/런타임 버전을 함께 기록하세요.

Ollama가 실행되지 않았다면 별도 PowerShell에서 다음을 실행한 채 두고 앱을 켭니다. 이미 서버가 실행 중이면 중복 실행하지 않습니다.

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
ollama serve
```

이는 현재 PowerShell과 자식 프로세스에만 적용되며 전역 환경을 변경하지 않습니다. 앱이 기존 Ollama를 재사용하면 그 프로세스의 설정은 변경하지 않습니다. 기존 서버의 클라우드 설정까지 끄려면 [공식 local-only 안내](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features)에 따라 서버를 다시 시작해야 합니다. 앱 코드는 고정 loopback의 로컬 모델만 요청합니다.

### 3. 확인 및 실행

```powershell
.\start-local.ps1 -CheckOnly
.\start-local.ps1
```

기본 주소는 http://127.0.0.1:8766/ 입니다. 다른 포트는 `-Port 8770`으로 지정합니다. `start.ps1`은 같은 인자를 전달하는 별칭입니다. 비밀번호/API 키를 입력하지 않으며 개발 서버 모드는 없습니다.

PowerShell 실행 정책에 막히면 전역 설정을 바꾸지 않고 이번 실행에만 적용합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start-local.ps1
```

`-CheckOnly`는 준비 상태만 확인하며 앱이나 Ollama를 새로 시작하지 않습니다. 일반 실행은 이미 실행 중인 로컬 Ollama를 먼저 사용합니다. 없으면 명시적 `-OllamaPath`, PATH, 표준 설치 위치, 호환 portable 위치 순서로 찾고 숨김 실행합니다. 모델이 없으면 자동 다운로드/대체 없이 실패합니다.

Portable 또는 별도 모델 경로를 사용할 경우 실제 설치에 맞게 지정합니다. 아래는 가상 경로 예시입니다.

```powershell
.\start-local.ps1 -OllamaPath 'D:\tools\ollama\ollama.exe' -ModelDirectory 'D:\models\ollama'
```

`-ModelDirectory`는 스크립트가 Ollama를 새로 시작할 때만 적용됩니다. 이미 실행 중이면 해당 서버가 사용하는 경로에 모델을 준비해야 합니다. 스크립트가 실행한 Ollama는 앱 종료 후에도 남을 수 있으며 필요한 경우 사용자가 종료합니다. 로그는 Git제외 `.local-runtime/`에만 둡니다.

## 모델 없이 계산 기능 확인

아래 방식은 Ollama의 설치/실행 없이 로컬 화면과 합성 계산 API를 켭니다. 자연어 질문은 모델이 없으면 실패하며 외부 서비스로 전환하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8766 --no-access-log
Invoke-RestMethod 'http://127.0.0.1:8766/api/retention/summary?program_code=DEMO-SWIM-A&base_month=2026-10&target_month=2026-11'
```

첫 명령은 서버를 계속 실행하므로 조회 명령은 다른 PowerShell에서 실행합니다. 기대값은 `source=mock, base_count=8, retained_count=6, retention_rate=75`입니다.

브라우저→로컬앱 API와 localhost Ollama HTTP 호출은 존재합니다. 업무용 API가 없다는 뜻이며 네트워크 요청 전체가0이라는 뜻은 아닙니다. 인터넷 서비스로 노출하는 배포 구성이 아닙니다.

## 질문과 기대 결과

- 2026년10월 A강습의11월 유지율 알려줘
- 2026년10월 A강습 수강생 중11월 미등록 명단 보여줘
- 2026년11월 전월보다 유지율이 하락한 강습을 찾아줘

합성5강습의9/10/11월 등록내역입니다. A강습10→11월은8명 중6명75%. 직전구간 대비 변화는 D−50%p,A−5%p,C0%p,E+50%p,B산출불가입니다. 이는 재신청만의 비율과 다르며 실제 업무 효과·하락 원인을 입증하지 않습니다.

계산은 코드,Tool선택은 모델 책임입니다. 회원행은 로컬표에만 표시하고 모델에는 집계/건수만 보냅니다. 요청당 모델4회·Tool6회,동시AI질문1개,자동재시도 없음입니다.

## 예시 작성·공개 범위

[합성 응답 기준](docs/MOCK_DATA_GUIDE.md),[응답 예시](examples/tool-responses.json),[새 Tool 틀](examples/new-tool-response-template.json)을 참고합니다. 실제 API는 권한내에서 업무 의미만 참고하고 실제응답/값/경로/매핑/내부구조를 복사하지 않습니다.

[공개 파일 기준](docs/PUBLICATION.md)에 따라 정확히 검토한 파일만 Git허용 목록에 둡니다. 내부검증 기록·장비/도구 사용 및 승인 증거는 비공개로 남깁니다. 새 예시/코드도 자동 허용하지 않고 파일·출처·비밀값을 검토한 뒤 목록을 갱신합니다.

[SECURITY.md](SECURITY.md)를 적용합니다. 현재Mock 전용 동작은 과거 전체 작업이Mock이었다거나 조직사용/공개가 승인되었다는 뜻이 아닙니다. Git 변경·외부 공유는 명시적으로 요청된 범위에서만 수행합니다. 공개 파일은 검토한 Mock 코드와 합성 예시로 한정합니다.
