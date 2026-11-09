import argparse
import json
from pathlib import Path

from rag.services import build_services

DEFAULT_QUESTIONS = Path(__file__).with_name("questions.json")
RANKINGS = ("score", "similarity", "keyword")


def rank_of_answer(candidates, pages, key):
    """1-based rank of the first Chunk from an expected page when ranked by key, or None if none was retrieved."""
    ranked = sorted(candidates, key=lambda chunk: chunk[key], reverse=True)
    return next((rank for rank, chunk in enumerate(ranked, start=1) if chunk["page"] in pages), None)


def evaluate(knowledge_base, document, questions, top_k, min_score):
    rows = []
    for item in questions:
        pages = set(item["pages"])
        candidates = [chunk for chunk in knowledge_base.candidates(item["question"]) if chunk["document"] == document]
        kept = knowledge_base.search(item["question"], top_k, min_score)
        rows.append(
            {
                "question": item["question"],
                "ranks": {key: rank_of_answer(candidates, pages, key) for key in RANKINGS},
                "kept": any(chunk["document"] == document and chunk["page"] in pages for chunk in kept),
                "kept_count": len(kept),
            }
        )
    return rows


def main(argv=None, storage_dir=None, ollama=None):
    parser = argparse.ArgumentParser(description="Measure how often retrieval finds the page that answers each question.")
    parser.add_argument("questions", type=Path, nargs="?", default=DEFAULT_QUESTIONS, help="Questions JSON file")
    args = parser.parse_args(argv)

    services = build_services(storage_dir, ollama)
    spec = json.loads(args.questions.read_text(encoding="utf-8"))
    document = spec["document"]
    if document not in {entry["name"] for entry in services.knowledge_base.documents()}:
        print(f"{document} is not in the knowledge base. Ingest it first: python -m rag.ingestion <path>")
        return 1

    top_k, min_score = services.top_k, services.min_score
    rows = evaluate(services.knowledge_base, document, spec["questions"], top_k, min_score)
    print(f"{'#':>2}  {'hybrid':>6}  {'dense':>5}  {'keyword':>7}  {'sent':>4}  question")
    for number, row in enumerate(rows, start=1):
        ranks = [str(row["ranks"][key] or "-") for key in RANKINGS]
        sent = f"{'yes' if row['kept'] else 'no'}/{row['kept_count']}"
        print(f"{number:>2}  {ranks[0]:>6}  {ranks[1]:>5}  {ranks[2]:>7}  {sent:>4}  {row['question']}")

    total = len(rows)
    hits = {key: sum(1 for row in rows if row["ranks"][key] and row["ranks"][key] <= top_k) for key in RANKINGS}
    print()
    print(f"Hit@{top_k}: hybrid {hits['score']}/{total}, dense only {hits['similarity']}/{total}, keyword only {hits['keyword']}/{total}")
    print(f"Answer page sent to the model (top {top_k}, score >= {min_score}): {sum(row['kept'] for row in rows)}/{total}")
    return 0
