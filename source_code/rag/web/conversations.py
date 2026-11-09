from flask import Blueprint, jsonify, request

from rag.ollama_client import OllamaError
from rag.retrieval.answerer import answer, citations
from rag.web.context import services

conversations_api = Blueprint("conversations", __name__, url_prefix="/api/conversations")

NOT_FOUND = {"error": "Conversation not found."}


@conversations_api.get("")
def list_conversations():
    return jsonify(services().conversations.list())


@conversations_api.post("")
def create_conversation():
    return jsonify(services().conversations.create()), 201


@conversations_api.get("/<int:conversation_id>")
def get_conversation(conversation_id):
    conversation = services().conversations.get(conversation_id)
    if conversation is None:
        return jsonify(NOT_FOUND), 404
    return jsonify(conversation)


@conversations_api.delete("/<int:conversation_id>")
def delete_conversation(conversation_id):
    if not services().conversations.delete(conversation_id):
        return jsonify(NOT_FOUND), 404
    return "", 204


@conversations_api.post("/<int:conversation_id>/messages")
def post_message(conversation_id):
    store = services().conversations
    if store.get(conversation_id) is None:
        return jsonify(NOT_FOUND), 404
    question = ((request.get_json(silent=True) or {}).get("question") or "").strip()
    if not question:
        return jsonify(error="Question must not be empty."), 400
    generation = answer(question, services().knowledge_base, services().ollama, services().top_k)
    if generation["error"]:
        store.log_generation(conversation_id, generation, services().llm_model)
        raise OllamaError(generation["error"])
    store.add_message(conversation_id, "user", question)
    reply = store.add_message(conversation_id, "assistant", generation["answer"], citations(generation))
    reply["generation_id"] = store.log_generation(conversation_id, generation, services().llm_model, reply["id"])
    return jsonify(reply), 201
