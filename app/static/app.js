const $ = (id) => document.getElementById(id);
let configured = false;
let busy = false;
let context = null;
let memberPage = null;
const registrationLabels = {new_registration: "새 등록", continuous_registration: "장기 등록 유지"};

function updateSend() {
  $("send").disabled = !configured || busy || !$("consent").checked;
  $("reset").disabled = busy;
  $("member-filter").disabled = busy;
  $("previous").disabled = busy || !memberPage || memberPage.offset === 0;
  $("next").disabled = busy || !memberPage || memberPage.offset + memberPage.limit >= memberPage.total;
}
function clearResults() {
  context = null;
  memberPage = null;
  $("context-label").textContent = "이전 조회 조건 없음";
  $("member-rows").replaceChildren();
  $("trend-rows").replaceChildren();
  $("traces").replaceChildren();
  $("answer").textContent = "";
  for (const id of ["answer-panel", "metrics", "members-panel", "trace-panel", "trend-panel"]) $(id).hidden = true;
}
function notice(message) { $("notice").textContent = message; $("notice").hidden = !message; }

async function api(path, options = {}) {
  const response = await fetch(path, {cache: "no-store", ...options});
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.message || "요청을 처리하지 못했습니다.");
    error.data = data;
    throw error;
  }
  return data;
}

async function refreshStatus() {
  try {
    const status = await api("/api/assistant/status");
    configured = status.configured;
    $("connection").textContent = `${status.model} · ${configured ? "로컬 연결됨" : "연결 준비 필요"}`;
    $("consent-label").textContent = "직접 만든 합성 데이터만 사용합니다. 업무 API 호출 없음 · 로컬 모델만 사용.";
    $("setup-title").textContent = "로컬 모델 실행 상태를 확인하세요.";
    $("setup-help").textContent = "프로젝트 폴더에서 .\\start-local.ps1을 실행하세요. Ollama와 qwen3:4b-instruct 모델이 필요합니다.";
    $("setup").hidden = configured;
  } catch (_) {
    configured = false;
    $("connection").textContent = "서버 연결 확인 필요";
    notice("서버에 연결하지 못했습니다. 실행 상태를 확인하세요.");
  }
  updateSend();
}

function showTraces(data) {
  $("trace-panel").hidden = false;
  const usage = data.usage;
  $("usage").textContent = usage ? `모델 요청 ${usage.request_count}회 · 보고된 입력 ${usage.input_tokens} / 출력 ${usage.output_tokens} 토큰` : "외부 호출 없음";
  $("traces").replaceChildren();
  for (const trace of data.traces || []) {
    const block = document.createElement("div");
    block.className = "trace";
    const label = document.createElement("strong");
    label.textContent = trace.tool;
    const time = document.createElement("span");
    time.className = "trace-time";
    time.textContent = `${trace.elapsed_ms} ms · 로컬 조회`;
    const values = document.createElement("pre");
    values.textContent = JSON.stringify({arguments: trace.arguments, result: trace.result}, null, 2);
    block.append(label, time, values);
    $("traces").append(block);
  }
}

function showTrend(trend) {
  $("trend-panel").hidden = false;
  $("trend-count").textContent = `분석 ${trend.analyzed_count}개 · 하락 조건 ${trend.declined_count}개 · 산출 불가 ${trend.not_calculable_count}개`;
  $("trend-scope").textContent = `${trend.scope} · 기준 시점 ${trend.dataset_as_of}`;
  $("trend-period").textContent = `${trend.previous_base_month} → ${trend.base_month} 대비 ${trend.base_month} → ${trend.target_month} · 최소 ${trend.min_drop_pp}%p 하락`;
  $("trend-definition").textContent = trend.definition;
  $("trend-rows").replaceChildren();
  const labels = {declined: "하락", increased: "상승", unchanged: "동일", not_calculable: "산출 불가"};
  const rate = (value, retained, base) => value === null ? `산출 불가 (${retained}/${base})` : `${value}% (${retained}/${base})`;
  for (const item of trend.items) {
    const row = document.createElement("tr");
    const values = [`${item.program.program_name} (${item.program.program_code})`,
      rate(item.previous_rate, item.previous_retained_count, item.previous_base_count),
      rate(item.current_rate, item.current_retained_count, item.current_base_count),
      item.change_pp === null ? "—" : item.change_pp === 0 && item.status === "declined" ? "0.01%p 미만 하락" : item.change_pp === 0 && item.status === "increased" ? "0.01%p 미만 상승" : `${item.change_pp > 0 ? "+" : ""}${item.change_pp} %p`,
      labels[item.status] + (item.meets_threshold ? " · 조건 충족" : "")];
    for (const value of values) { const cell = document.createElement("td"); cell.textContent = value; row.append(cell); }
    const cell = document.createElement("td");
    const button = document.createElement("button");
    button.type = "button"; button.className = "secondary"; button.textContent = "미재등록 명단 질문";
    button.addEventListener("click", () => {
      if (busy) return;
      context = {program_code: item.program.program_code, base_month: trend.base_month, target_month: trend.target_month};
      $("context-label").textContent = `선택한 강습: ${context.program_code} · ${context.base_month} → ${context.target_month}`;
      $("message").value = "이 강습의 미재등록 명단 보여줘";
      $("message").focus();
    });
    cell.append(button); row.append(cell); $("trend-rows").append(row);
  }
  if (!trend.items.length) {
    const row = document.createElement("tr"); const cell = document.createElement("td");
    cell.colSpan = 6; cell.textContent = "분석 대상 강습이 없습니다."; row.append(cell); $("trend-rows").append(row);
  }
}

function showMembers(page) {
  memberPage = page;
  $("members-panel").hidden = false;
  $("member-total").textContent = `${page.total}명`;
  $("member-filter").value = page.status;
  $("member-rows").replaceChildren();
  for (const member of page.members) {
    const row = document.createElement("tr");
    const values = [member.member_id, member.display_name,
      member.status === "retained" ? "유지" : "등록 미확인",
      registrationLabels[member.registration_type] || "—"];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    $("member-rows").append(row);
  }
  if (!page.members.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.textContent = "해당 조건의 대상자가 없습니다.";
    row.append(cell);
    $("member-rows").append(row);
  }
  $("page-label").textContent = page.total ? `${page.offset + 1}–${Math.min(page.offset + page.limit, page.total)} / ${page.total}` : "0명";
  $("previous").disabled = page.offset === 0;
  $("next").disabled = page.offset + page.limit >= page.total;
}

async function loadMembers(offset) {
  if (!context || busy) return;
  busy = true;
  updateSend();
  try {
    const query = new URLSearchParams({...context, status: $("member-filter").value, offset, limit: 20});
    showMembers(await api(`/api/retention/members?${query}`));
    notice("");
  } catch (error) { notice(error.message); }
  finally { busy = false; updateSend(); }
}

$("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy || !configured || !$("consent").checked) return;
  const message = $("message").value.trim();
  if (!message) return;
  busy = true;
  updateSend();
  $("send").textContent = "조회 중…";
  notice("질문을 해석하고 있습니다. 전체 강습 분석은 대상 수에 따라 오래 걸릴 수 있습니다. 자동 재시도하지 않습니다.");
  for (const id of ["answer-panel", "metrics", "members-panel", "trace-panel", "trend-panel"]) $(id).hidden = true;
  try {
    const data = await api("/api/assistant/chat", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message, context, approved_data_only: true})});
    context = data.context;
    $("answer").textContent = data.answer;
    $("answer-panel").hidden = false;
    $("context-label").textContent = context ? `이전 조회: ${context.program_code} · ${context.base_month} → ${context.target_month} (후속 질문에 사용)` : "이전 조회 조건 없음";
    if (data.summary) {
      const s = data.summary;
      $("metrics").hidden = false;
      $("rate").textContent = s.retention_rate === null ? "산출 불가" : `${s.retention_rate}%`;
      $("base-count").textContent = `${s.base_count}명`;
      $("retained-count").textContent = `${s.retained_count}명`;
      $("retained-detail").textContent = s.new_registration_count === null ? "새 재신청 / 장기 유지 구분 미확인" : `새 등록 ${s.new_registration_count} · 장기 유지 ${s.continuous_registration_count}`;
      $("data-footer").textContent = `기준 시점 ${s.dataset_as_of} · ${s.source === "development" ? "개발 API 현재 상태 조회" : "합성 데이터"} · ${s.definition}`;
      $("missing-count").textContent = `${s.not_retained_count}명`;
    }
    if (data.trend) showTrend(data.trend);
    if (data.members) showMembers(data.members);
    showTraces(data);
    notice(data.status === "clarification" ? "조회가 완료되지 않았습니다. 아래 안내에 따라 질문을 구체화하세요." : "");
  } catch (error) {
    notice(error.message);
    if (error.data) showTraces(error.data);
  } finally {
    busy = false;
    $("send").textContent = "질문하기 ↗";
    updateSend();
  }
});

document.querySelectorAll("[data-example]").forEach((button) => button.addEventListener("click", () => {
  $("message").value = button.dataset.example;
  $("message").focus();
}));
$("consent").addEventListener("change", updateSend);
$("refresh-status").addEventListener("click", refreshStatus);
$("reset").addEventListener("click", () => {
  if (busy) return;
  context = null;
  memberPage = null;
  $("message").value = "";
  $("context-label").textContent = "이전 조회 조건 없음";
  for (const id of ["answer-panel", "metrics", "members-panel", "trace-panel", "trend-panel"]) $(id).hidden = true;
  notice("");
});
$("member-filter").addEventListener("change", () => loadMembers(0));
$("previous").addEventListener("click", () => loadMembers(Math.max(0, memberPage.offset - memberPage.limit)));
$("next").addEventListener("click", () => loadMembers(memberPage.offset + memberPage.limit));
refreshStatus();
