"""파이프라인 진입점. UI와 평가 하네스가 공유하는 유일한 경로."""
from __future__ import annotations

from dataclasses import dataclass

import guard
import llm
import prompt


@dataclass
class AdvisorResult:
    answer: str
    report: guard.GuardReport


def advise(query: str, temperature: float = 0.2) -> AdvisorResult:
    messages = prompt.build_messages(query)
    answer = llm.chat(messages, temperature=temperature)
    report = guard.review(answer)
    if report.unverified and not report.is_refusal:
        answer += (
            "\n\n※ 참고: "
            + ", ".join(report.unverified)
            + "의 일부 수치는 교차검증 진행 중인 통용값입니다."
        )
    return AdvisorResult(answer=answer, report=report)


def advise_structured(current: str, application: str, priority: str) -> AdvisorResult:
    return advise(f"현재 냉매: {current} / 용도: {application} / 우선순위: {priority}")
