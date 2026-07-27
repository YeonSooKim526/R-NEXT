"""Streamlit 챗 UI. advisor 호출과 가드 결과 표시만 담당한다.

실행: streamlit run app/ui.py
"""
from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

import advisor
import guard
import llm
import loader

PRIORITIES = ["GWP(환경규제 대응)", "안전(불연 유지)", "효율", "장기 규제 안정성"]
APPLICATIONS = [
    "상업용 에어컨",
    "가정용 에어컨",
    "데이터센터 칠러",
    "대형 건물 칠러(원심·터보)",
    "슈퍼마켓 냉동(쇼케이스)",
    "산업용 냉동·냉장창고",
    "가정용 냉장고",
    "차량 에어컨",
    "히트펌프(급탕·난방)",
    "직접 입력…",
]
EXAMPLE_QUERIES = [
    "R-410A의 GWP는 얼마인가요?",
    "R-22를 대체할 저GWP 냉매 추천",
    "데이터센터 칠러용 불연(A1) 냉매는?",
]
LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "consultations.jsonl"


def logo_svg(size: int, uid: str) -> str:
    """육각 눈결정 아이콘 — 로딩 스피너 전용."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad-{uid}" x1="0" y1="0" x2="48" y2="48">
      <stop offset="0" stop-color="#38bdf8"/>
      <stop offset="1" stop-color="#2563eb"/>
    </linearGradient>
  </defs>
  <g stroke="url(#grad-{uid})" stroke-width="3.2" stroke-linecap="round">
    <g id="arm-{uid}">
      <line x1="24" y1="24" x2="24" y2="5"/>
      <line x1="24" y1="10" x2="19.5" y2="5.5"/>
      <line x1="24" y1="10" x2="28.5" y2="5.5"/>
    </g>
    <use href="#arm-{uid}" transform="rotate(60 24 24)"/>
    <use href="#arm-{uid}" transform="rotate(120 24 24)"/>
    <use href="#arm-{uid}" transform="rotate(180 24 24)"/>
    <use href="#arm-{uid}" transform="rotate(240 24 24)"/>
    <use href="#arm-{uid}" transform="rotate(300 24 24)"/>
    <circle cx="24" cy="24" r="3.2" fill="url(#grad-{uid})" stroke="none"/>
  </g>
</svg>"""


def icecube_svg(size: int, uid: str) -> str:
    """연하늘색 계열의 입체 아이스큐브 로고(표정 없음) — 타이틀·아바타용."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
  <g stroke-linejoin="round" stroke-linecap="round">
    <path d="M24 6 L40 15 L24 24 L8 15 Z" fill="#ecf8ff"/>
    <path d="M8 15 L24 24 L24 41 L8 32 Z" fill="#cfeefe"/>
    <path d="M40 15 L24 24 L24 41 L40 32 Z" fill="#aee0fb"/>
    <path d="M24 6 L40 15 L40 32 L24 41 L8 32 L8 15 Z" fill="none"
          stroke="#7cc8f5" stroke-width="2.6"/>
    <path d="M8 15 L24 24 L40 15 M24 24 L24 41" stroke="#7cc8f5" stroke-width="2"
          opacity="0.8" fill="none"/>
    <path d="M19 12.5 L25.5 9 L29.5 11.2 L23 14.8 Z" fill="#ffffff" opacity="0.8"/>
    <line x1="12" y1="28.5" x2="12" y2="21.5" stroke="#ffffff" stroke-width="2.2" opacity="0.75"/>
    <line x1="30" y1="35.5" x2="36" y2="29" stroke="#ffffff" stroke-width="2" opacity="0.45"/>
    <circle cx="33.5" cy="10" r="1.4" fill="#ffffff" opacity="0.9"/>
  </g>
</svg>"""


LOADING_HTML = f"""<div style="display:flex;align-items:center;gap:10px;padding:6px 0;">
<span class="rnext-spin">{logo_svg(24, "spin")}</span>
<span style="opacity:0.7;">냉매 레퍼런스를 근거로 답변을 작성하는 중입니다…</span>
</div>
<style>
.rnext-spin svg {{ animation: rnext-rot 1.8s linear infinite; display: block; }}
@keyframes rnext-rot {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
</style>"""

AVATAR_ASSISTANT = "data:image/svg+xml;base64," + base64.b64encode(
    icecube_svg(32, "avatar").encode()
).decode()
AVATAR_USER = "💬"

st.set_page_config(page_title="R-NEXT", page_icon="🧊", layout="centered")
st.markdown(
    """<style>
    [data-testid="stStatusWidget"] { visibility: hidden; }
    [data-testid="stAppDeployButton"] { display: none; }
    /* 답변 속 핵심(굵은 글씨)을 연한 개나리색 형광펜 스타일로 강조 */
    [data-testid="stChatMessage"] p strong,
    [data-testid="stChatMessage"] li strong,
    [data-testid="stChatMessage"] td strong {
        background: #fef9c3;
        padding: 0 0.15em;
        border-radius: 0.2em;
    }
    /* 주요 버튼(전환 상담 요청)을 짙은 네이비 계열로 */
    button[kind="primary"],
    [data-testid="stBaseButton-primary"] {
        background-color: #1e3a8a !important;
        border-color: #1e3a8a !important;
    }
    button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover {
        background-color: #172c6e !important;
        border-color: #172c6e !important;
    }
    /* 예시 질문 버튼은 작고 연하게 */
    button[kind="secondary"],
    [data-testid="stBaseButton-secondary"] {
        font-size: 0.72rem !important;
        padding: 0.15rem 0.45rem !important;
        min-height: 1.65rem !important;
        color: #475569 !important;
        border-color: #cbd5e1 !important;
    }
    button[kind="secondary"] p,
    [data-testid="stBaseButton-secondary"] p { font-size: 0.72rem !important; }
    /* 사이드바 폰트 체계: 입력 폼과 상담 기록을 0.8rem으로 통일 */
    [data-testid="stSidebar"] h2 { font-size: 1.05rem; }
    [data-testid="stSidebar"] label p { font-size: 0.8rem !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] div { font-size: 0.8rem; }
    [data-testid="stSidebar"] input { font-size: 0.8rem; }
    [data-testid="stSidebar"] button p { font-size: 0.85rem !important; }
    /* 사이드바 상담 기록(tertiary 버튼): 평소엔 좌측 정렬 일반 텍스트,
       호버·클릭 시에만 테두리 없는 연블루 블록 — ChatGPT 목록 스타일 */
    [data-testid="stSidebar"] [data-testid="stBaseButton-tertiary"] {
        justify-content: flex-start !important;
        padding: 0.18rem 0.45rem !important;
        border-radius: 0.45rem !important;
        color: #475569 !important;
    }
    [data-testid="stSidebar"] [data-testid="stBaseButton-tertiary"]:hover,
    [data-testid="stSidebar"] [data-testid="stBaseButton-tertiary"]:active {
        background: #e3efff !important;
        color: #1e3a8a !important;
    }
    /* 버전별 DOM 차이 대비: kind 속성·내부 컨테이너까지 좌측 정렬 강제 */
    [data-testid="stSidebar"] button[kind="tertiary"] {
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] [data-testid="stBaseButton-tertiary"] > div,
    [data-testid="stSidebar"] button[kind="tertiary"] > div,
    [data-testid="stSidebar"] [data-testid="stBaseButton-tertiary"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] button[kind="tertiary"] [data-testid="stMarkdownContainer"] {
        width: 100% !important;
        text-align: left !important;
        margin: 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stBaseButton-tertiary"] p,
    [data-testid="stSidebar"] button[kind="tertiary"] p {
        font-size: 0.72rem !important;
        text-align: left !important;
    }
    /* 출처 블록: 사이드바 흐름 최하단, 작은 폰트 (고정 배치는 폭 불일치·겹침을 유발해 제거) */
    .rnext-sources {
        font-size: 0.68rem;
        color: #94a3b8;
        line-height: 1.8;
        margin-top: 0.4rem;
    }
    </style>""",
    unsafe_allow_html=True,
)
st.markdown(
    f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:0.2rem;">
    {icecube_svg(40, "title")}
    <span style="font-size:2.3rem;font-weight:700;letter-spacing:0.02em;color:#1e3a8a;">R-NEXT</span>
    </div>""",
    unsafe_allow_html=True,
)
st.markdown(
    """<div style="font-size:0.85rem;color:#6b7280;line-height:1.5;margin:0 0 0.9rem;">
    지금 사용 중인 냉매와 용도를 입력하면, 규제에 맞는 대체 냉매(R-?)와 전환 시점을 근거와 함께 추천하는 시스템입니다.<br>
    <span style="font-size:0.78rem;color:#9ca3af;">국산 AI(EXAONE) 기반 · 입력 정보는 외부 전송 없이 로컬에서만 처리됩니다.</span>
    </div>""",
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []


def log_turn(query: str, result) -> None:
    """상담 기록을 JSONL로 남긴다. 로깅 실패가 상담을 막아서는 안 된다."""
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        r = result.report
        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "model": llm.MODEL,
            "query": query,
            "answer": result.answer,
            "guard": {
                "passed": r.passed,
                "is_refusal": r.is_refusal,
                "gwp_mismatches": r.gwp_mismatches,
                "safety_mismatches": r.safety_mismatches,
                "unknown_refs": r.unknown_refs,
                "offtable_props": r.offtable_props,
            },
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_title(query: str) -> str:
    """상담 기록 목록에 쓸 짧은 제목 — ChatGPT식 대화 제목 방식.

    상담 폼 입력('현재 냉매: … / 용도: … / …')은 핵심만 추려 제목화하고,
    자유 질문은 앞부분을 잘라 쓴다.
    """
    if query.startswith("현재 냉매:"):
        try:
            parts = [p.split(":", 1)[1].strip() for p in query.split("/")]
            return f"{parts[0]} · {parts[1]} 전환 상담"
        except IndexError:
            pass
    t = query.strip().rstrip("?.!").strip()
    return t if len(t) <= 26 else t[:25] + "…"


def recent_logs(limit: int = 6) -> list[dict]:
    try:
        lines = LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return []
    entries = []
    for line in reversed(lines[-limit:]):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def render_report(report) -> None:
    if report.gwp_mismatches:
        st.error("⚠️ 그라운딩 불일치 감지 — 아래 수치는 레퍼런스 표와 다릅니다:\n\n"
                 + "\n".join(f"- {m}" for m in report.gwp_mismatches))
    elif not report.is_refusal:
        st.success("✅ 답변 속 GWP 수치가 레퍼런스 표와 일치합니다.")
    if report.safety_mismatches:
        st.warning("안전등급 표기 확인 필요:\n\n"
                   + "\n".join(f"- {m}" for m in report.safety_mismatches))
    if report.unknown_refs:
        st.info("레퍼런스 표 외 냉매 언급: " + ", ".join(report.unknown_refs))
    if report.offtable_props:
        st.warning("⚠️ 표에 없는 속성(" + ", ".join(report.offtable_props)
                   + ")에 대한 답변입니다 — 수치 근거가 레퍼런스 표에 없으므로 공식 물성 자료로 확인하세요.")


def run(query: str) -> None:
    st.session_state.history.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=AVATAR_USER):
        st.markdown(query)
    # 로딩 중에는 아바타 없는 회전 아이콘만 표시하고,
    # 답변이 도착한 뒤에야 아이스큐브 아바타가 달린 메시지로 렌더링한다.
    slot = st.empty()
    slot.markdown(LOADING_HTML, unsafe_allow_html=True)
    try:
        result = advisor.advise(query)
    except RuntimeError as e:
        slot.empty()
        st.error(str(e))
        st.session_state.history.pop()
        return
    slot.empty()
    with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
        st.markdown(result.answer)
        render_report(result.report)
    log_turn(query, result)
    st.session_state.history.append(
        {"role": "assistant", "content": result.answer, "report": result.report}
    )


with st.sidebar:
    st.header("전환 상담 입력")
    numbers = [r["ashrae_number"] for r in loader.refrigerants()]
    current = st.selectbox("현재 냉매", numbers, index=numbers.index("R-22"))
    app_choice = st.selectbox("적용 용도", APPLICATIONS)
    if app_choice == "직접 입력…":
        application = st.text_input("적용 용도 직접 입력",
                                    placeholder="예: 운송 냉동, 초저온 냉동(-80℃)")
    else:
        application = app_choice
    priority = st.selectbox("우선순위", PRIORITIES)
    if st.button("전환 상담 요청", type="primary", use_container_width=True):
        if application.strip():
            st.session_state.pending = f"현재 냉매: {current} / 용도: {application} / 우선순위: {priority}"
        else:
            st.warning("적용 용도를 입력해 주세요.")

    st.divider()
    st.markdown('<div style="font-size:0.85rem;font-weight:600;color:#334155;">상담 기록</div>',
                unsafe_allow_html=True)
    logs = recent_logs()
    if logs:
        # 기록을 누르면 해당 상담이 채팅창에 다시 열린다.
        # tertiary = 테두리·배경 없는 텍스트형 버튼(기본 좌측 정렬).
        for i, e in enumerate(logs):
            if st.button(log_title(e.get("query", "")), key=f"log-{i}",
                         type="tertiary", use_container_width=True):
                g = e.get("guard", {})
                report = guard.GuardReport(
                    is_refusal=g.get("is_refusal", False),
                    gwp_mismatches=g.get("gwp_mismatches", []),
                    safety_mismatches=g.get("safety_mismatches", []),
                    unknown_refs=g.get("unknown_refs", []),
                    offtable_props=g.get("offtable_props", []),
                )
                st.session_state.history = [
                    {"role": "user", "content": e.get("query", "")},
                    {"role": "assistant", "content": e.get("answer", ""), "report": report},
                ]
    else:
        st.markdown('<div style="font-size:0.8rem;color:#94a3b8;">아직 상담 기록이 없습니다.</div>',
                    unsafe_allow_html=True)

    # 출처: 사이드바 흐름의 최하단 요소로 배치 (겹침 없음)
    st.divider()
    st.markdown(
        f"""<div class="rnext-sources">
        <b>냉매 레퍼런스 {len(numbers)}종 수록</b><br>
        데이터 출처<br>
        · ASHRAE Standard 34 (UNEP·ASHRAE 팩트시트)<br>
        · EU F-gas 규정 (EU) 2024/573<br>
        · IPCC AR4 · AR6<br>
        · 환경부 냉매관리제도 고시
        </div>""",
        unsafe_allow_html=True,
    )

chat_area = st.container()
with chat_area:
    for turn in st.session_state.history:
        avatar = AVATAR_USER if turn["role"] == "user" else AVATAR_ASSISTANT
        with st.chat_message(turn["role"], avatar=avatar):
            st.markdown(turn["content"])
            if turn["role"] == "assistant" and turn.get("report") is not None:
                render_report(turn["report"])

# 중앙 입력 영역: 입력창(인라인) + 바로 아래 작은 예시 질문 버튼.
# chat_input은 컨테이너 안에 넣어야 화면 하단 고정이 아니라 본문 흐름에 렌더링된다.
if not st.session_state.history:
    st.markdown('<div style="height:14vh"></div>', unsafe_allow_html=True)
with st.container():
    typed = st.chat_input("질문을 입력하세요")
    cols = st.columns(len(EXAMPLE_QUERIES))
    for i, example in enumerate(EXAMPLE_QUERIES):
        if cols[i].button(example, key=f"example-{i}", use_container_width=True):
            st.session_state.pending = example
if typed:
    st.session_state.pending = typed

if query := st.session_state.pop("pending", None):
    with chat_area:
        run(query)
