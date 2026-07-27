# R-NEXT — 냉매 전환 가이드

국산 소형 LLM(EXAONE 3.5 7.8B, Ollama 로컬 실행) 기반 냉매 전환 의사결정 지원 도구.
"지금 냉매의 다음 답(R-?)"을 규제 근거와 함께 추천한다.
설계 문서: [냉매전환어드바이저_설계서.md](냉매전환어드바이저_설계서.md)

## 빠른 시작

```bash
# 1. 모델 준비 (최초 1회, 약 5GB)
brew install ollama          # 미설치 시
ollama serve                 # 별도 터미널에서
ollama pull exaone3.5:7.8b

# 2. 파이썬 환경
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. 앱 실행
streamlit run app/ui.py

# 4. 평가 (그라운딩 정확도·환각률)
python3 eval/run_eval.py            # 전체 16문항
python3 eval/run_eval.py --ids E01  # 단건 확인
```

다른 모델을 쓰려면: `OLLAMA_MODEL=kanana:8b streamlit run app/ui.py`

## 구조

```
data/       # 그라운딩 데이터 (냉매 표 33종·규제 요약·few-shot·평가셋) — data/README.md 참조
app/
├── loader.py    # data/ 로딩·마크다운 직렬화 (사실의 단일 원천)
├── prompt.py    # 제약 시스템 프롬프트 + few-shot 대화 턴 조립
├── llm.py       # Ollama OpenAI 호환 클라이언트
├── guard.py     # 답변 수치를 표와 대조하는 결정론적 환각 검증
├── advisor.py   # 파이프라인 진입점 (UI·평가 공용)
└── ui.py        # Streamlit 챗 UI
eval/
└── run_eval.py  # 평가 하네스 → eval/results/에 결과 저장
```

핵심 원리: 사실은 전부 `data/reference/refrigerants.json`에서 오고(프롬프트 주입),
같은 파일이 가드 계층의 정답지로도 쓰여 답변 속 수치가 기계적으로 검증된다.

> **라이선스 유의**: EXAONE 3.5 모델은 비상업(NC) 라이선스입니다. 본 저장소는 교육·연구
> 목적의 코드이며, 모델 가중치는 포함하지 않습니다(각자 `ollama pull`로 수령).
