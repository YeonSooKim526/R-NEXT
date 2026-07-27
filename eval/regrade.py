#!/usr/bin/env python3
"""저장된 평가 결과(모델 답변)를 현재 버전의 guard·채점기로 재채점한다.

채점기를 고친 뒤 모델을 다시 돌리지 않고도 공정한 수치를 얻는 용도.
실행: python3 eval/regrade.py eval/results/eval_*.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "eval"))

import guard  # noqa: E402
from run_eval import grade  # noqa: E402


def main() -> None:
    items = {
        i["id"]: i
        for i in json.loads(
            (ROOT / "data" / "eval" / "eval_set.json").read_text(encoding="utf-8")
        )["items"]
    }
    for path in sys.argv[1:]:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        results = d["results"]
        for r in results:
            report = guard.review(r["answer"])
            r["passed"], r["hallucination"] = grade(items[r["id"]], r["answer"], report)
            r["gwp_mismatches"] = report.gwp_mismatches
            r["safety_mismatches"] = report.safety_mismatches
        traps = [r for r in results if r["type"] == "hallucination_trap"]
        normal = [r for r in results if r["type"] != "hallucination_trap"]
        d["summary"]["grounding_accuracy"] = round(sum(r["passed"] for r in normal) / len(normal), 3)
        d["summary"]["hallucination_rate"] = round(sum(r["hallucination"] for r in results) / len(results), 3)
        d["summary"]["trap_refusal"] = f"{sum(r['passed'] for r in traps)}/{len(traps)}"
        d["summary"]["regraded"] = True
        out = Path(path).with_name(Path(path).stem + "_regraded.json")
        out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        s = d["summary"]
        fails = [f"{r['id']}({'환각' if r['hallucination'] else '오답'})" for r in results if not r["passed"]]
        print(f"{s['model']}: grounding={s['grounding_accuracy']} halluc={s['hallucination_rate']} "
              f"traps={s['trap_refusal']} | 실패: {', '.join(fails) or '없음'}")


if __name__ == "__main__":
    main()
