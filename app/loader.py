"""data/ 로딩·직렬화 계층. 앱 시작 시 1회 로딩해 캐시한다.

refrigerants.json이 사실의 단일 원천이며, 여기서 만든 lookup은
프롬프트(참고서)와 guard(정답지)가 공유한다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

TABLE_COLUMNS = [
    ("ashrae_number", "번호"),
    ("name", "명칭"),
    ("family", "계열"),
    ("composition", "조성(질량%)"),
    ("gwp100", "GWP100(기준)"),
    ("odp", "ODP"),
    ("safety_class", "안전등급"),
    ("applications", "대표 용도"),
    ("alternatives", "대체냉매"),
    ("reg_category", "규제구분"),
    ("regulatory_status", "규제 상태"),
    ("notes", "비고"),
]


@lru_cache(maxsize=1)
def refrigerants() -> list[dict]:
    data = json.loads((DATA / "reference" / "refrigerants.json").read_text(encoding="utf-8"))
    return data["refrigerants"]


@lru_cache(maxsize=1)
def by_number() -> dict[str, dict]:
    """R번호 → 항목. '(E)'/'(Z)' 없는 표기도 함께 등록해 조회를 관대하게 한다."""
    index: dict[str, dict] = {}
    for r in refrigerants():
        num = r["ashrae_number"]
        index[num] = r
        stripped = num.replace("(E)", "").replace("(Z)", "")
        index.setdefault(stripped, r)
    return index


@lru_cache(maxsize=1)
def regulations_md() -> str:
    return (DATA / "reference" / "regulations_summary.md").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def few_shots() -> list[dict]:
    data = json.loads((DATA / "prompts" / "few_shot_examples.json").read_text(encoding="utf-8"))
    return data["examples"]


def _cell(r: dict, key: str) -> str:
    value = r.get(key)
    if value is None:
        return "-"
    if isinstance(value, list):
        return "; ".join(value)
    if key == "gwp100":
        text = f"{value} ({r['gwp_basis']})"
        if r.get("needs_verification"):
            text += " ⚠️검증중"
        return text
    return str(value)


@lru_cache(maxsize=1)
def table_markdown() -> str:
    header = "| " + " | ".join(label for _, label in TABLE_COLUMNS) + " |"
    divider = "|" + "---|" * len(TABLE_COLUMNS)
    rows = [
        "| " + " | ".join(_cell(r, key) for key, _ in TABLE_COLUMNS) + " |"
        for r in refrigerants()
    ]
    return "\n".join([header, divider, *rows])
