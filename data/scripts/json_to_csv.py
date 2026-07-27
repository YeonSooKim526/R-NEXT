#!/usr/bin/env python3
"""refrigerants.json → refrigerants.csv 변환. 수정은 항상 JSON에서 하고 이 스크립트로 CSV를 재생성한다."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "reference" / "refrigerants.json"
DST = ROOT / "reference" / "refrigerants.csv"

FIELDS = [
    "ashrae_number", "name", "family", "composition", "gwp100", "gwp_basis",
    "odp", "safety_class", "applications", "alternatives", "reg_category",
    "regulatory_status", "notes", "sources", "needs_verification",
]


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = data["refrigerants"]
    with DST.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            row = dict(r)
            for key in ("applications", "alternatives", "sources"):
                row[key] = "; ".join(row.get(key) or [])
            writer.writerow({k: row.get(k, "") for k in FIELDS})
    print(f"{len(rows)} rows -> {DST}")


if __name__ == "__main__":
    main()
