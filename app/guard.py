"""가드 계층 — 모델 답변을 refrigerants.json과 기계적으로 대조하는 결정론적 방어.

프롬프트 제약(확률적 방어)이 뚫렸을 때 잡아내는 2차 방어선이며,
평가 하네스의 환각 판정에도 그대로 쓰인다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import loader

REF_RE = re.compile(r"R-\d{2,4}[a-z]{0,3}[A-Z]?(?:\((?:E|Z)\))?")
# '<150' 같은 임계치 표기(GWP<150)는 수치 주장이 아니므로 <, > 뒤 숫자는 제외.
NUM_RE = re.compile(r"(?<![A-Za-z\d./<>-])(\d{1,5}(?:\.\d+)?)")
LT_ONE_RE = re.compile(r"<1(?!\d)|1 미만")
SAFE_RE = re.compile(r"(?<![A-Za-z0-9-])(A2L|B2L|A1|A2|A3|B1|B2|B3)\b")

SECTION_MARKERS = ["【추천 냉매】", "【GWP 비교】", "【안전등급】", "【전환 시 고려사항】", "【규제 시점】"]
REFUSAL_MARKERS = [
    "표에 없", "레퍼런스 표에 없", "모릅니다", "모른다",
    "알 수 없", "답변드릴 수 없", "답할 수 없", "정보가 없",
    "포함되어 있지 않", "포함되지 않", "등록되지 않", "기재되어 있지 않",
    "기재되지 않", "수록되지 않", "존재하지 않",
]
# 숫자 뒤에 이 접미가 오면 GWP 주장이 아니다(연도·비율·임계치·단위 서술 등).
NON_GWP_SUFFIXES = ("%", "년", "℃", "°", "대", "초과", "이상", "이하", "미만", "kW", "kg", "g", "톤")
# '1387-1397' / '1387~1397' 병기 범위의 뒤 끝값도 주장으로 수집한다.
RANGE_RE = re.compile(r"\d{1,5}(?:\.\d+)?\s*[-~–]\s*(\d{1,5}(?:\.\d+)?)")
# '약 1387 (R-448A)'처럼 값이 토큰 앞에 오는 역순 표기의 후방 귀속 확인용.
BACKWARD_RE = re.compile(r"(\d{1,5}(?:\.\d+)?|<1)\s*\(\s*$")

# GWP 귀속 윈도. 넓으면 'R-448A는 …를 포함하고 있으며, GWP가 약 1387' 같은
# 문장에서 뒤쪽 절의 수치를 중간에 언급된 다른 냉매에 오귀속한다.
# 표에 없는 속성 키워드 — 이 주제에 수치로 답하면 근거가 표에 없다는 뜻이다.
OFFTABLE_PROPERTIES = ("임계온도", "임계압력", "포화압력", "증기압", "비등점", "냉동능력", "COP")

GWP_WINDOW = 18
# 안전등급은 'R-32: A2L(…)'처럼 토큰 직후에 붙는 표기만 귀속시킨다.
# 윈도가 넓으면 '불연(A1)이 필수라면 …' 같은 일반 서술이 앞 냉매에 오귀속된다.
SAFE_WINDOW = 12


@dataclass
class GuardReport:
    is_refusal: bool = False
    has_schema: bool = False
    gwp_mismatches: list[str] = field(default_factory=list)
    safety_mismatches: list[str] = field(default_factory=list)
    unknown_refs: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    offtable_props: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """핵심 통과 기준: 수치 환각(GWP 불일치)이 없을 것."""
        return not self.gwp_mismatches


def _gwp_claims(text: str, start: int, end: int) -> list[str]:
    """[start, end) 구간의 GWP 주장('<1' 또는 숫자)을 모두 수집한다.

    - 접미사 판정은 잘린 윈도가 아니라 원문 기준('2030년'의 '년' 경계 잘림 방지).
    - 'ODP 0.055'처럼 ODP 문맥의 수치는 GWP 주장이 아니므로 제외.
    - '1387~1397' 같은 범위·병기 표기를 위해 전부 수집하고,
      호출부에서 '하나라도 표와 일치하면 통과'로 판정한다.
    """
    claims: list[str] = []
    window = text[start: end + 2]  # '<1'이 경계에 걸치는 경우 대비 +2
    if LT_ONE_RE.search(window):
        claims.append("<1")
    for m in NUM_RE.finditer(text, start):
        if m.start() >= end:
            break
        if "ODP" in text[start: m.start()].upper():
            continue
        tail = text[m.end():].lstrip()
        if tail.startswith(NON_GWP_SUFFIXES):
            continue
        # '규제 요약> 1. 몬트리올' 같은 서수·항목 번호는 주장이 아니다.
        if text[m.end(): m.end() + 1] == ".":
            continue
        claims.append(m.group(1))
    for m in RANGE_RE.finditer(window):
        claims.append(m.group(1))
    return claims


def _gwp_matches(claim: str, table_value) -> bool:
    if claim == "<1":
        return table_value == "<1"
    if table_value == "<1":
        # 표의 '<1'을 '약 1'로 옮기는 것은 수치 조작이 아니다.
        try:
            return float(claim) <= 1.5
        except ValueError:
            return False
    try:
        return abs(float(claim) - float(table_value)) <= 2
    except (TypeError, ValueError):
        return False


def review(answer: str) -> GuardReport:
    report = GuardReport(
        is_refusal=any(marker in answer for marker in REFUSAL_MARKERS),
        has_schema=all(marker in answer for marker in SECTION_MARKERS),
    )
    if not report.is_refusal:
        report.offtable_props = [p for p in OFFTABLE_PROPERTIES if p in answer]
    index = loader.by_number()
    seen_unknown: set[str] = set()
    seen_unverified: set[str] = set()

    for m in REF_RE.finditer(answer):
        token = m.group()
        entry = index.get(token)
        if entry is None:
            if token not in seen_unknown:
                seen_unknown.add(token)
                report.unknown_refs.append(token)
            continue

        num = entry["ashrae_number"]
        if entry.get("needs_verification") and num not in seen_unverified:
            seen_unverified.add(num)
            report.unverified.append(num)

        # 윈도는 다음 냉매 토큰 앞에서 끝난다 — 그 뒤 수치는 다음 냉매의 것이므로.
        nxt = REF_RE.search(answer, m.end())
        limit = nxt.start() if nxt else len(answer)

        if not answer[m.end(): m.end() + 1] == "/":  # 'R-32/125 (50.0/50.0)' 같은 조성 표기 문맥은 건너뜀
            claims = _gwp_claims(answer, m.end(), min(m.end() + GWP_WINDOW, limit))
            # '약 1387 (R-448A)' 역순 표기: 토큰 직전의 값도 이 냉매의 주장이다.
            back = BACKWARD_RE.search(answer[max(0, m.start() - 16): m.start()])
            if back:
                claims.append(back.group(1))
            if claims and not any(_gwp_matches(c, entry["gwp100"]) for c in claims):
                report.gwp_mismatches.append(
                    f"{num}: 답변 GWP {'/'.join(claims)} ↔ 표 {entry['gwp100']}"
                )

        safe = SAFE_RE.search(answer[m.end(): min(m.end() + SAFE_WINDOW, limit)])
        if safe and safe.group(1) != entry["safety_class"]:
            report.safety_mismatches.append(
                f"{num}: 답변 등급 {safe.group(1)} ↔ 표 {entry['safety_class']}"
            )
    return report
