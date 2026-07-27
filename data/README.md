# data/ — 냉매 전환 어드바이저 데이터셋

설계서([냉매전환어드바이저_설계서.md](../냉매전환어드바이저_설계서.md)) 3-1절의 데이터 요구사항을 구현한 초안(v0.1).

## 구조

```
data/
├── README.md                      # 이 파일
├── SOURCES.md                     # 전체 출처 목록·데이터 사용 원칙
├── reference/                     # [Phase 1] 그라운딩 지식 (프롬프트 주입 대상)
│   ├── refrigerants.json          # 냉매 속성 표 33종 — 핵심 데이터
│   ├── refrigerants.csv           # 위 JSON의 CSV 뷰 (검수·스프레드시트용, JSON에서 자동 생성)
│   └── regulations_summary.md     # 규제 레퍼런스 요약 (키갈리·HCFC·환경부 고시·EU F-gas·PFAS)
├── prompts/                       # [Phase 2] 프롬프트 자산
│   └── few_shot_examples.json     # 골드 예시 4쌍 (형식 고정 3 + 거절 예시 1)
├── eval/                          # [Phase 4] 평가
│   └── eval_set.json              # 16문항 (fact 6 / recommendation 5 / regulation 2 / 환각 트랩 3)
├── corpus/                        # [Phase 5 확장] RAG용 규제 원문 청크 (현재 비어 있음)
└── scripts/
    └── json_to_csv.py             # JSON → CSV 재생성 스크립트
```

## refrigerants.json 스키마

| 필드 | 설명 |
|---|---|
| `ashrae_number` | R번호 (예: R-32) |
| `name` | 화학명/통칭 (한국어) |
| `family` | 계열: CFC / HCFC / HFC / HFO / HCFO / 자연냉매 / 블렌드 |
| `composition` | 블렌드 조성 질량% (순수냉매는 null) |
| `gwp100`, `gwp_basis` | GWP100 값과 기준(AR4 기본, HFO는 AR5/AR6) — **기준 명시 필수** |
| `odp` | 오존파괴지수 |
| `safety_class` | ASHRAE 34 안전등급 (A1~B3) |
| `applications` | 대표 용도 |
| `alternatives` | 대표 대체냉매 |
| `reg_category` | 퇴출완료 / 감축중 / 감축대상 / 저GWP대체 / 비대상 |
| `regulatory_status` | 규제 상태 서술 |
| `sources` | 출처 키 (SOURCES.md 참조) |
| `needs_verification` | true면 교차검증 미완 — 답변 시 단서 필요 |

## 유지보수 규칙

1. **수정은 refrigerants.json에서만** 하고, CSV는 재생성한다:
   ```bash
   cd data && python3 scripts/json_to_csv.py
   ```
2. 수치 변경 시 반드시 `sources`를 함께 갱신한다.
3. `needs_verification: true` 항목을 검증하면 플래그를 해제하고 출처를 추가한다.
4. 규제 일정 항목은 ⚠️ 표시(regulations_summary.md)를 원문 확인 후 제거한다.
