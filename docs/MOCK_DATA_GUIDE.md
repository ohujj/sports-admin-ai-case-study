# 합성 데이터와 가정 응답 작성 기준

## 목적과 경계

이 문서는 미래 Tool에 필요한 응답 예시를 만드는 기준입니다. 실제 API 계약이나 원문을 재현하는 것이 아니라, 업무 의미를 일반화해 독립적인 가상 계약을 설계합니다. 예시는 저장된 로컬 값이며 업무 서버 호출·인증·DB 연결이 없습니다. 로컬 모델 호출은 자연어 해석에만 사용합니다.

## 작성 순서

1. 어떤 업무 질문을 보조할지 일반 문장으로 정의합니다. 예: 한 강습의 월별 유지 여부를 비교한다.
2. 모델 판단에 꼭 필요한 정보와 코드 계산에 필요한 정보를 나눕니다. 예: 모델은 강습·월·집계, 계산은 합성 월별 회원 집합.
3. 참고 권한이 있는 API가 있다면 필요한 의미·null/빈목록·기간/페이징 개념만 확인합니다. 이 프로젝트에서 서버를 호출해 예시를 추출하지 않습니다. API 문서/사내 소스를 모델 프롬프트·공개 문서에 복사하지 않습니다.
4. 필드 이름·포맷·식별값·상태·오류 메시지는 이 데모에서 독립적으로 정합니다. endpoint/내부 모델/에러코드/DB와의 매핑표를 만들지 않습니다.
5. 모든 값은 직접 만듭니다. 실제 응답을 가명화/마스킹/순서변경한 값도 사용하지 않습니다. 회사 고유 강습코드 대신 DEMO-* 같은 독립 식별자를 씁니다.
6. provenance에 synthetic=true, origin=hand_authored, business_api_called=false, hypothesis와 기대값을 남깁니다. 미래에도 원문 캡처/덤프/화면/네트워크 로그는 fixture에 포함하지 않습니다.
7. 정상/빈집합/분모0/중복/잘못된기간/지원하지않는대상을 합성으로 만들고 계산 기대값과 대조합니다. 회사명·내부계약·자격증명·개인정보·서버/DB 경로 포함 여부도 검사합니다.

## 구성

- app/mock_data.py: 실행에 쓰는 합성 등록행 원천. 직접 작성한 fixture이며 외부 데이터 수집 기능이 없습니다.
- examples/tool-responses.json: 현재 fixture로 계산한 Tool별 응답 예시. 생성 결과를 저장한 참고용이며 런타임이 실제 서버처럼 호출하는 파일은 아닙니다.
- examples/new-tool-response-template.json: 미래 기능의 가정 응답 작성 틀. 실제 API 필드를 채워 넣는 템플릿이 아닙니다.

모델은 read_programs/read_retention_summary/read_retention_declines의 카탈로그·집계 또는 show_retention_members의 건수만 받습니다. 회원 행은 로컬 표시 데이터이며 모델 응답 예시에는 포함하지 않습니다.

## 예시

```json
{
  "provenance": {
    "synthetic": true,
    "origin": "hand_authored",
    "business_api_called": false,
    "hypothesis": "같은 강습의 가상 월별 회원 집합을 비교한다"
  },
  "assumed_result": {"base_count": 8, "retained_count": 6, "retention_rate": 75}
}
```

75는 합성 fixture의 기대값이며 실제 기관의 통계가 아닙니다. 오류는 실패로 반환하고 실제 응답 수집으로 fallback하지 않습니다.
