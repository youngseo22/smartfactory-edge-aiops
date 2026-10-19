"""[Stage 5] Vertex AI RAG 매뉴얼 검색 에이전트.

- LocalKnowledgeBase : manual_kb.json 을 경량 TF-IDF 벡터 스토어로 인덱싱 (의존성 없음)
- RagAgent.diagnose  : 이상 이벤트 → 검색 쿼리 구성 → Top-k 매뉴얼 청크 검색 → 진단 결과
- USE_GCP=true 이면 검색된 컨텍스트를 Vertex AI Gemini 에 전달해 조치 키워드를 생성
  (실패 시 로컬 RAG 결과로 자동 폴백). LangChain/LlamaIndex 리트리버로 교체 가능하도록
  `Retriever` 프로토콜만 지키면 된다.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol

from config import settings
from models.schemas import EventType, PipelineEvent

log = logging.getLogger("rag")

KB_PATH = Path(__file__).with_name("manual_kb.json")
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[._][a-z0-9]+)*|[가-힣]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for tok in _TOKEN_RE.findall(text.lower()):
        tokens.append(tok)
        if re.fullmatch(r"[가-힣]+", tok) and len(tok) > 2:  # 한글 bi-gram 보강
            tokens.extend(tok[i : i + 2] for i in range(len(tok) - 1))
    return tokens


@dataclass
class RetrievedChunk:
    chunk: dict[str, Any]
    score: float


@dataclass
class Diagnosis:
    event_type: EventType
    page: str
    title: str
    keyword: str
    secondary: str
    icon: str
    metric: str
    confidence: float
    source: str = "LOCAL_RAG"
    references: list[str] = field(default_factory=list)


class Retriever(Protocol):
    def search(self, query: str, k: int = 3, event_type: Optional[str] = None) -> list[RetrievedChunk]: ...


class LocalKnowledgeBase:
    """순수 파이썬 TF-IDF + 코사인 유사도 벡터 스토어."""

    def __init__(self, path: Path = KB_PATH) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.documents = {d["doc_id"]: d for d in data["documents"]}
        self.chunks: list[dict[str, Any]] = data["chunks"]
        docs_tokens = [self._chunk_tokens(c) for c in self.chunks]
        df: Counter[str] = Counter()
        for toks in docs_tokens:
            df.update(set(toks))
        n = len(self.chunks)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        self.vectors = [self._vectorize(toks) for toks in docs_tokens]

    @staticmethod
    def _chunk_tokens(c: dict[str, Any]) -> list[str]:
        text = " ".join([c["title"], c["content"], " ".join(c.get("tags", [])) * 2, c.get("equipment", "")])
        return tokenize(text)

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        vec = {t: (1 + math.log(f)) * self.idf.get(t, 1.0) for t, f in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, k: int = 3, event_type: Optional[str] = None) -> list[RetrievedChunk]:
        q = self._vectorize(tokenize(query))
        results = []
        for chunk, vec in zip(self.chunks, self.vectors):
            score = sum(w * vec.get(t, 0.0) for t, w in q.items())
            if event_type and event_type in chunk.get("event_types", []):
                score += 0.35  # 메타데이터 필터 부스트
            results.append(RetrievedChunk(chunk, round(score, 4)))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]


QUERY_TEMPLATES: dict[EventType, str] = {
    EventType.VIBRATION_ANOMALY: "cap motor bearing vibration svm torque 캡 조립 모터 베어링 진동 토크 조절",
    EventType.BACKLOG_HIGH: "pubsub backlog queue worker scale dataflow 큐 적체 스케일",
    EventType.NODE_DOWN: "coldchain node heartbeat failover backup zone 콜드체인 노드 단절 백업 우회",
    EventType.TEMP_HIGH: "coldchain temperature hvac zone 콜드체인 온도 이탈",
}


class RagAgent:
    def __init__(self, retriever: Optional[Retriever] = None) -> None:
        self.retriever: Retriever = retriever or LocalKnowledgeBase()
        self._vertex: Any = None
        if settings.use_gcp:
            try:
                import vertexai  # type: ignore
                from vertexai.generative_models import GenerativeModel  # type: ignore

                vertexai.init(project=settings.gcp_project or None, location=settings.gcp_location)
                self._vertex = GenerativeModel(settings.vertex_model)
                log.info("Vertex AI enabled (%s)", settings.vertex_model)
            except Exception as exc:  # noqa: BLE001
                log.warning("Vertex AI unavailable, local RAG only: %s", exc)

    def build_query(self, event: PipelineEvent) -> str:
        base = QUERY_TEMPLATES.get(event.event_type, event.event_type.value)
        extras = " ".join(f"{k} {v}" for k, v in event.payload.items())
        return f"{base} {event.source} {extras}"

    async def diagnose(self, event: PipelineEvent) -> Diagnosis:
        hits = self.retriever.search(self.build_query(event), k=3, event_type=event.event_type.value)
        top = hits[0].chunk
        action = top.get("action", {})
        metric_key = action.get("metric_key", "")
        metric_val = event.payload.get(metric_key)
        diag = Diagnosis(
            event_type=event.event_type,
            page=top["page"],
            title=top["title"],
            keyword=action.get("keyword", ""),
            secondary=action.get("secondary", ""),
            icon=action.get("icon", "info"),
            metric=f"{metric_key.upper()} {metric_val}" if metric_val is not None else "",
            confidence=min(0.99, round(0.55 + hits[0].score / 2, 2)),
            references=[h.chunk["page"] for h in hits],
        )
        if self._vertex is not None:
            diag = await self._refine_with_gemini(event, hits, diag)
        return diag

    async def _refine_with_gemini(
        self, event: PipelineEvent, hits: list[RetrievedChunk], diag: Diagnosis
    ) -> Diagnosis:  # pragma: no cover - requires GCP
        context = "\n\n".join(f"[{h.chunk['page']}] {h.chunk['title']}\n{h.chunk['content']}" for h in hits)
        prompt = (
            "You are an AIOps agent for a cosmetics smart factory. Using ONLY the manual context, "
            "return JSON {\"page\":str,\"keyword\":str (<=4 words action, e.g. 'Torque -0.5 Turn'),"
            "\"confidence\":float}.\n\n"
            f"EVENT: {event.model_dump_json()}\n\nCONTEXT:\n{context}"
        )
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(
                    self._vertex.generate_content,
                    prompt,
                    generation_config={"response_mime_type": "application/json", "temperature": 0.1},
                ),
                timeout=4.0,
            )
            data = json.loads(resp.text)
            diag.page = data.get("page", diag.page)
            diag.keyword = data.get("keyword", diag.keyword)
            diag.confidence = float(data.get("confidence", diag.confidence))
            diag.source = "VERTEX_AI"
        except Exception as exc:  # noqa: BLE001
            log.warning("Gemini refine failed, fallback local: %s", exc)
        return diag
