from flask import Blueprint, jsonify, request

from rag.web.context import services

rag_api = Blueprint("rag", __name__, url_prefix="/api")

DEFAULT_PER_PAGE = 50
DEFAULT_THRESHOLD = 0.5
DEFAULT_MAX_RESULTS = 20
MAX_RESULTS_LIMIT = 100


def _positive_int(value, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


@rag_api.get("/chunks")
def list_chunks():
    document = request.args.get("document", "")
    text = request.args.get("q", "").strip().lower()
    page = _positive_int(request.args.get("page"), 1)
    per_page = min(_positive_int(request.args.get("per_page"), DEFAULT_PER_PAGE), 200)
    chunks = [
        chunk
        for chunk in services().knowledge_base.chunks()
        if (not document or chunk["document"] == document) and text in chunk["text"].lower()
    ]
    start = (page - 1) * per_page
    return jsonify(chunks=chunks[start : start + per_page], total=len(chunks), page=page, per_page=per_page)


@rag_api.post("/search")
def search():
    body = request.get_json(silent=True) or {}
    query = str(body.get("query") or "").strip()
    threshold = body.get("threshold", DEFAULT_THRESHOLD)
    max_results = body.get("max_results", DEFAULT_MAX_RESULTS)
    if not query:
        return jsonify(error="Query must not be empty."), 400
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
        return jsonify(error="Threshold must be a number between 0 and 1."), 400
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= MAX_RESULTS_LIMIT:
        return jsonify(error=f"Max results must be a whole number from 1 to {MAX_RESULTS_LIMIT}."), 400
    results = services().knowledge_base.search(query, max_results)
    return jsonify([result for result in results if result["similarity"] >= threshold])
