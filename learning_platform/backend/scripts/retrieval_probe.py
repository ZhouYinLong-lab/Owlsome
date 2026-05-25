from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.pipelines.importer import import_sample
from app.services.notes import find_best_match
from app.services.retrieval import config_from_env, load_knowledge_documents, search_knowledge_points


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe optional BGE retrieval matching against public knowledge points.")
    parser.add_argument("--query", required=True, help="笔记或题目文本")
    parser.add_argument("--top-k", type=int, default=None, help="embedding 召回数量")
    parser.add_argument("--rerank-top-k", type=int, default=None, help="reranker 输出数量")
    parser.add_argument("--ensure-sample", action="store_true", help="知识库为空时先导入样例")
    args = parser.parse_args()

    config = config_from_env()
    if args.ensure_sample and not load_knowledge_documents():
        result = import_sample()
        print(f"sample_import: ok={result.ok}, message={result.message}")

    docs = load_knowledge_documents()
    print(f"provider: {config.provider}")
    print(f"embedding_model: {config.embedding_model}")
    print(f"reranker_model: {config.reranker_model}")
    print(f"documents: {len(docs)}")

    match = search_knowledge_points(args.query, top_k=args.top_k, rerank_top_k=args.rerank_top_k)
    print(f"retrieval_fallback: {match.fallback}")
    print(f"retrieval_reason: {match.reason}")

    if match.candidates:
        print("retrieval_candidates:")
        for index, candidate in enumerate(match.candidates, start=1):
            print(
                f"{index}. kp={candidate.knowledge_point_id} "
                f"{candidate.code} {candidate.title} score={candidate.score} reason={candidate.reason}"
            )
    else:
        print("retrieval_candidates: none")

    best_id, reason = find_best_match(args.query)
    print(f"final_match_id: {best_id}")
    print(f"final_reason: {reason}")


if __name__ == "__main__":
    main()
