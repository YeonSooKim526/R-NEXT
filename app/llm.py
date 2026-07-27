"""Ollama 네이티브 /api/chat 클라이언트.

OpenAI 호환 엔드포인트(/v1/chat/completions)는 num_ctx를 받지 않아
기본 4096 컨텍스트로 프롬프트 앞부분(제약 규칙·냉매 표)이 잘린다 —
그라운딩이 통째로 무력화되므로 반드시 네이티브 API로 num_ctx를 명시한다.
"""
from __future__ import annotations

import os

import requests

BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "exaone3.5:7.8b")
# 프롬프트 ~7.2K토큰 + 답변 여유. 18GB 통합 메모리에서 KV 캐시 부담 없음.
NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "16384"))


def chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 1200) -> str:
    try:
        resp = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": NUM_CTX,
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
            timeout=(5, 600),
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Ollama 서버({BASE_URL})에 연결할 수 없습니다. "
            "터미널에서 `ollama serve` 실행 여부와 "
            f"`ollama pull {MODEL}` 완료 여부를 확인하세요."
        ) from e
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama 응답 오류: {resp.status_code} {resp.text[:300]}") from e
    data = resp.json()
    if data.get("prompt_eval_count", 0) >= NUM_CTX:
        raise RuntimeError(
            f"프롬프트({data['prompt_eval_count']}토큰)가 컨텍스트(NUM_CTX={NUM_CTX})를 초과했습니다. "
            "OLLAMA_NUM_CTX를 늘리세요 — 잘린 프롬프트로는 그라운딩이 깨집니다."
        )
    return data["message"]["content"]
