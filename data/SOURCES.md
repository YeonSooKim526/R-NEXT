# 데이터 출처 목록

데이터셋 구축·교차검증에 사용한 공개 출처. (탐색·검증일: 2026-07-20)

## 냉매 속성 (GWP·ODP·안전등급·조성)

| 키 | 출처 | 용도 | 링크 |
|---|---|---|---|
| UNEP-ASHRAE | UNEP×ASHRAE Factsheet "Update on New Refrigerants Designations and Safety Classifications" | 안전등급·블렌드 조성 공식 검증 (무료 PDF) | [2018.06판](https://ozone.unep.org/system/files/documents/UPDATED-Factsheet_ASHRAE_English_20180625_printer-11X17.pdf) · [2022.11판](https://www.ashrae.org/file%20library/technical%20resources/bookstore/factsheet_ashrae_english_november2022.pdf) |
| ASHRAE | ASHRAE Refrigerant Designations (최신 등재 현황) | 신규 R번호 확인 | [링크](https://www.ashrae.org/technical-resources/standards-and-guidelines/ashrae-refrigerant-designations) |
| EU-2024-573 | EU F-gas Regulation (EU) 2024/573 Annex I·II | GWP 법정 수치(AR4/AR6)·규제 상태 | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/573/oj/eng) |
| IPCC-AR4 / IPCC-AR6 | IPCC AR4 GWP100 / AR6 WG1 Table 7.SM.7 | GWP 과학적 원출처 | [AR6 Ch.7 SM PDF](https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_Chapter_07_Supplementary_Material.pdf) · [GitHub](https://github.com/IPCC-WG1/Chapter-7) |
| WIKI | Wikipedia "List of refrigerants" (CC BY-SA) | 표 뼈대 부트스트랩·교차검증 | [링크](https://en.wikipedia.org/wiki/List_of_refrigerants) |
| DCCEEW | 호주 정부 HFC GWP·안전등급 표 | 보조 교차검증 (접속 불안정) | [링크](https://www.dcceew.gov.au/environment/protection/ozone/rac/global-warming-potential-values-hfc-refrigerants) |

## 국내 규제·제도

| 출처 | 용도 | 링크 |
|---|---|---|
| 냉매사용기기의 냉매관리기준 규정 (환경부 고시 제2025-165호) | 국내 냉매관리제도 근거 원문 | [법령정보센터](https://law.go.kr/LSW/admRulLsInfoP.do?admRulSeq=2100000265378) |
| 대기환경보전법·시행규칙 | 상위 법령 | [법령정보센터](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=608) |
| 국가법령정보 공동활용 Open API | Phase 5 RAG 코퍼스 수집(원문 XML/JSON, 무료 가입) | [open.law.go.kr](https://open.law.go.kr/) |
| 공공데이터포털 — 한국환경공단 냉매관리제도 (파일 CSV/JSON/XML + Open API 2종: 냉매관리제도 정보, 냉매회수업체 정보) | 국내 제도·회수업체 데이터 | [data.go.kr 검색 "냉매"](https://www.data.go.kr/) |
| UNEP 오존사무국 (몬트리올·키갈리) | 국제협약 일정 원출처 | [ozone.unep.org](https://ozone.unep.org/) |

## 데이터 사용 원칙

1. **GWP 기본 기준은 AR4** — 키갈리·EU F-gas Annex I과 정합. HFO/HCFO는 AR5/AR6 근사값 사용, 항목별 `gwp_basis`에 명시.
2. `needs_verification: true` 항목(현재 5종: R-600a, R-1270, R-455A, R-514A, R-515B)은 제조사 기술자료·EUR-Lex 원문으로 교차검증 후 플래그 해제.
3. Wikipedia는 뼈대·교차검증용으로만 쓰고, 답변 근거의 최종 출처는 공식 문서(UNEP-ASHRAE, EUR-Lex, IPCC)로 귀속시킨다.
