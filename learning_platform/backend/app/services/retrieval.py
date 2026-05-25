from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.db import get_connection, rows_to_dicts


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parents[1]

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)


@dataclass
class RetrievalConfig:
    provider: str
    embedding_base_url: str
    embedding_api_key: str
    embedding_model: str
    reranker_base_url: str
    reranker_api_key: str
    reranker_model: str
    top_k: int
    rerank_top_k: int
    timeout_seconds: float


@dataclass
class RetrievalCandidate:
    knowledge_point_id: int
    code: str
    title: str
    score: float
    reason: str


@dataclass
class RetrievalMatch:
    candidates: list[RetrievalCandidate]
    provider: str
    fallback: bool
    reason: str


def config_from_env() -> RetrievalConfig:
    return RetrievalConfig(
        provider=os.getenv("RETRIEVAL_PROVIDER", "off").strip().lower() or "off",
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL", "").strip().rstrip("/"),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", "").strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3").strip(),
        reranker_base_url=os.getenv("RERANKER_BASE_URL", "").strip().rstrip("/"),
        reranker_api_key=os.getenv("RERANKER_API_KEY", "").strip(),
        reranker_model=os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3").strip(),
        top_k=max(1, int(os.getenv("RETRIEVAL_TOP_K", "8"))),
        rerank_top_k=max(1, int(os.getenv("RERANK_TOP_K", "3"))),
        timeout_seconds=max(1.0, float(os.getenv("RETRIEVAL_TIMEOUT_SECONDS", "30"))),
    )


def load_knowledge_documents(limit_chars: int = 2200) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT id, code, title, summary, tags, raw_markdown
                FROM knowledge_points
                ORDER BY order_index
                """
            ).fetchall()
        )
    documents = []
    for row in rows:
        text = "\n".join(
            [
                str(row["code"]),
                str(row["title"]),
                str(row["summary"]),
                str(row["tags"]),
                str(row["raw_markdown"] or "")[:limit_chars],
            ]
        )
        documents.append({**row, "doc_id": f"kp:{row['id']}", "text": text})
    return documents


def search_knowledge_points(query: str, top_k: int | None = None, rerank_top_k: int | None = None) -> RetrievalMatch:
    config = config_from_env()
    if config.provider == "off":
        return RetrievalMatch([], config.provider, True, "RETRIEVAL_PROVIDER=off，使用规则匹配 fallback。")
    if config.provider not in {"openai_compatible", "custom_http"}:
        return RetrievalMatch([], config.provider, True, f"未知检索 provider: {config.provider}。")
    if not config.embedding_base_url:
        return RetrievalMatch([], config.provider, True, "未配置 EMBEDDING_BASE_URL。")

    documents = load_knowledge_documents()
    if not documents:
        return RetrievalMatch([], config.provider, True, "知识库为空，请先导入样例。")

    try:
        requested_top_k = top_k or config.top_k
        query_vector = embed_texts(config, [query])[0]
        doc_vectors = embed_texts(config, [doc["text"] for doc in documents])
        scored = []
        for doc, vector in zip(documents, doc_vectors):
            scored.append((cosine_similarity(query_vector, vector), doc))
        scored.sort(reverse=True, key=lambda item: item[0])
        ranked = scored[:requested_top_k]

        reranked = rerank_documents(config, query, ranked, rerank_top_k or config.rerank_top_k)
        if reranked:
            ranked = reranked

        candidates = [
            RetrievalCandidate(
                knowledge_point_id=int(doc["id"]),
                code=str(doc["code"]),
                title=str(doc["title"]),
                score=round(float(score), 4),
                reason=f"{config.provider} 检索匹配到 {doc['code']} {doc['title']}，score={score:.4f}。",
            )
            for score, doc in ranked[: (rerank_top_k or config.rerank_top_k)]
        ]
        if not candidates:
            return RetrievalMatch([], config.provider, True, "检索服务未返回候选结果。")
        return RetrievalMatch(candidates, config.provider, False, "retrieval")
    except Exception as exc:
        return RetrievalMatch([], config.provider, True, f"检索服务不可用，已回退规则匹配：{type(exc).__name__}: {exc}")


def find_best_match_by_retrieval(query: str) -> tuple[int | None, str] | None:
    match = search_knowledge_points(query)
    if match.fallback or not match.candidates:
        return None
    best = match.candidates[0]
    return best.knowledge_point_id, best.reason


def embed_texts(config: RetrievalConfig, texts: list[str]) -> list[list[float]]:
    if config.provider == "openai_compatible":
        payload = {"model": config.embedding_model, "input": texts}
        data = post_json(f"{config.embedding_base_url}/embeddings", payload, config.embedding_api_key, config.timeout_seconds)
        embeddings = [item["embedding"] for item in data.get("data", [])]
    else:
        payload = {"model": config.embedding_model, "texts": texts}
        data = post_json(f"{config.embedding_base_url}/embed", payload, config.embedding_api_key, config.timeout_seconds)
        embeddings = data.get("embeddings", [])
    if len(embeddings) != len(texts):
        raise ValueError(f"embedding 数量不匹配：期望 {len(texts)}，得到 {len(embeddings)}")
    return [[float(value) for value in vector] for vector in embeddings]


def rerank_documents(
    config: RetrievalConfig,
    query: str,
    ranked: list[tuple[float, dict[str, Any]]],
    top_k: int,
) -> list[tuple[float, dict[str, Any]]]:
    if not config.reranker_base_url:
        return []
    payload = {
        "model": config.reranker_model,
        "query": query,
        "documents": [{"id": doc["doc_id"], "text": doc["text"]} for _score, doc in ranked],
        "top_k": top_k,
    }
    try:
        data = post_json(f"{config.reranker_base_url}/rerank", payload, config.reranker_api_key, config.timeout_seconds)
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        return []

    by_id = {doc["doc_id"]: doc for _score, doc in ranked}
    reranked = []
    for item in data.get("results", []):
        doc = by_id.get(str(item.get("id")))
        if doc:
            reranked.append((float(item.get("score", 0)), doc))
    return reranked


def post_json(url: str, payload: dict[str, Any], api_key: str, timeout: float) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("向量维度不一致。")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
