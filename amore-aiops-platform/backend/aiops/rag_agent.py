"""Stage 5 — 사내 설비 매뉴얼 RAG 에이전트.

LocalRagAgent : 경량 BM25 검색(의존성 없음) + 규칙 기반 진단  → mock 모드
VertexRagAgent: 동일 검색 + Vertex AI(Gemini) 로 원인/조치 생성 → gcp 모드 (실패 시 Local 로 폴백)
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from config import settings
from models.schemas import AlertEvent

log = logging.getLogger("aiops.rag")
KB_PATH = Path(__file__).with_name("manual_kb.json")

QUERY_BY_EVENT = {
    "VIBRATION_HIGH": "모터 진동 vibration svm 베어링 마모 토크 torque 캡 조립 과부하",
    "BACKLOG_HIGH": "큐 적체 backlog 주문 폭주 워커 scale 병목",
    "NODE_DOWN": "콜드체인 센서 노드 단절 heartbeat failover 백업 zone",
    "TEMP_HIGH": "콜드체인 온도 습도 이상 zone",
}


class Diagnosis(BaseModel):
    cause: str
    manual_page: int
    manual_title: str
    key_action: str
    confidence: float
    summary: str = ""


def _tokens(text: str) -> list[str]:
    toks: list[str] = []
    for w in re.findall(r"\w+", text.lower()):
        toks.append(w)
        if re.search(r"[가-힣]", w) and len(w) > 1:  # 한글: 문자 bi-gram 추가
            toks.extend(w[i : i + 2] for i in range(len(w) - 1))
    return toks


class ManualKnowledgeBase:
    """구조화된 지식 베이스 + BM25 검색 (임베딩 벡터 스토어의 경량 대체)."""

    def __init__(self, path: Path = KB_PATH, k1: float = 1.5, b: float = 0.75) -> None:
        self.docs: list[dict] = json.loads(path.read_text(encoding="utf-8"))
        self.k1, self.b = k1, b
        self._tf = [Counter(_tokens(" ".join([d["title"], " ".join(d["keywords"]), d["content"]]))) for d in self.docs]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = sum(self._len) / len(self._len)
        df: Counter = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self.docs)
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, top_k: int = 3) -> list[tuple[dict, float]]:
        q = _tokens(query)
        scored = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                f = self._tf[i].get(t, 0)
                if f:
                    s += self._idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self._len[i] / self._avg))
            scored.append((d, s))
        return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]


class RagAgent(Protocol):
    async def diagnose(self, event: AlertEvent, context: dict) -> Diagnosis: ...


class LocalRagAgent:
    def __init__(self) -> None:
        self.kb = ManualKnowledgeBase()

    async def diagnose(self, event: AlertEvent, context: dict) -> Diagnosis:
        query = QUERY_BY_EVENT.get(event.type, event.type)
        doc, score = self.kb.search(query, top_k=1)[0]
        return Diagnosis(
            cause=doc["cause"],
            manual_page=doc["page"],
            manual_title=doc["title"],
            key_action=doc["key_action"],
            confidence=round(min(0.99, score / (score + 4.0)), 2),
            summary=doc["content"],
        )


class VertexRagAgent(LocalRagAgent):
    """검색은 로컬 KB, 최종 진단 생성은 Gemini (Vertex AI)."""

    def __init__(self) -> None:
        super().__init__()
        import vertexai  # lazy import
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=settings.gcp_project, location=settings.vertex_location)
        self._model = GenerativeModel(settings.vertex_model)

    async def diagnose(self, event: AlertEvent, context: dict) -> Diagnosis:
        base = await super().diagnose(event, context)
        try:
            prompt = (
                "너는 스마트팩토리 AIOps 에이전트다. 아래 매뉴얼 발췌와 센서 컨텍스트로 원인을 진단하고 "
                'JSON {"cause": str, "key_action": str, "summary": str} 만 출력하라.\n'
                f"[매뉴얼 p.{base.manual_page}] {base.manual_title}\n{base.summary}\n"
                f"[이벤트] {event.model_dump()}\n[컨텍스트] {context}"
            )
            resp = await self._model.generate_content_async(
                prompt, generation_config={"response_mime_type": "application/json"}
            )
            data = json.loads(resp.text)
            return base.model_copy(update={k: data[k] for k in ("cause", "key_action", "summary") if k in data})
        except Exception:
            log.exception("Vertex AI 호출 실패 → 로컬 진단 결과 사용")
            return base


def make_rag_agent() -> RagAgent:
    if settings.use_gcp:
        try:
            return VertexRagAgent()
        except Exception:
            log.exception("Vertex AI 초기화 실패 → 로컬 RAG 로 대체")
    return LocalRagAgent()
