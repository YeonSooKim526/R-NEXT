#!/usr/bin/env python3
"""평가 하네스 — eval_set.json을 프로덕션과 동일한 advisor 파이프라인으로 돌려
grounding_accuracy와 hallucination_rate를 산출한다.

실행:  python3 eval/run_eval.py [--limit N] [--ids E01,E14]
결과:  eval/results/eval_YYYYMMDD_HHMM.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from advisor import advise  # noqa: E402

# 자유서술형 골드를 채점 가능한 키워드로 낮춘 항목별 오버라이드.
# 각 원소는 "이 중 하나라도 답변에 있으면 충족"인 대안 그룹이다.
OVERRIDES: dict[str, list[list[str]]] = {
    "E04": [["<1", "1 미만", "약 1"]],  # 표의 '<1'을 '약 1'로 표현해도 정답
    "E05": [["0.055"], ["HCFC"]],
    # 조성은 '44.0/52.0/4.0'뿐 아니라 'R-125(44.0%), …' 표기도 정답 —
    # 판별력 있는 두 성분비(44, 52)의 동시 등장으로 채점한다.
    "E06": [["44"], ["52"]],
    "E13": [["2030"]],
}


def _alts(value) -> list[str]:
    if isinstance(value, (int, float)):
        return [str(value), f"{value:,}"]
    return [str(value)]


def requirement_groups(item: dict) -> list[list[str]]:
    if item["id"] in OVERRIDES:
        return OVERRIDES[item["id"]]
    return [_alts(v) for v in item["gold"].get("expected_facts", {}).values()]


def grade(item: dict, answer: str, report) -> tuple[bool, bool]:
    """returns (passed, hallucination_event)"""
    gold = item["gold"]
    if gold.get("must_refuse"):
        refused = report.is_refusal
        return refused, not refused
    halluc = bool(report.gwp_mismatches)
    if item["type"] == "recommendation":
        hit = any(ref in answer for ref in gold["expected_refrigerants"])
        return hit and not halluc, halluc
    ok = all(any(alt in answer for alt in group) for group in requirement_groups(item))
    return ok and not halluc, halluc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", type=str, default=None, help="예: E01,E14")
    args = ap.parse_args()

    items = json.loads((ROOT / "data" / "eval" / "eval_set.json").read_text(encoding="utf-8"))["items"]
    if args.ids:
        wanted = set(args.ids.split(","))
        items = [i for i in items if i["id"] in wanted]
    if args.limit:
        items = items[: args.limit]

    print(f"평가 시작: {len(items)}문항 (로컬 추론 — 문항당 수십 초 소요)\n")
    results, t0 = [], time.time()
    for item in items:
        result = advise(item["question"])
        passed, halluc = grade(item, result.answer, result.report)
        mark = "PASS" if passed else "FAIL"
        extra = " [환각]" if halluc else ""
        print(f"  {item['id']} {item['type']:<18} {mark}{extra}")
        results.append({
            "id": item["id"], "type": item["type"], "question": item["question"],
            "answer": result.answer, "passed": passed, "hallucination": halluc,
            "gwp_mismatches": result.report.gwp_mismatches,
            "safety_mismatches": result.report.safety_mismatches,
        })

    traps = [r for r in results if r["type"] == "hallucination_trap"]
    normal = [r for r in results if r["type"] != "hallucination_trap"]
    grounding = sum(r["passed"] for r in normal) / len(normal) if normal else 0.0
    halluc_rate = sum(r["hallucination"] for r in results) / len(results) if results else 0.0

    from llm import MODEL, NUM_CTX
    summary = {
        "model": MODEL,
        "num_ctx": NUM_CTX,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "n_items": len(results),
        "grounding_accuracy": round(grounding, 3),
        "hallucination_rate": round(halluc_rate, 3),
        "trap_refusal": f"{sum(r['passed'] for r in traps)}/{len(traps)}",
        "elapsed_sec": round(time.time() - t0, 1),
    }
    print("\n=== 결과 ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"eval_{datetime.now():%Y%m%d_%H%M}.json"
    out.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n저장: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
