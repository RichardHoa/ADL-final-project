from flask import Blueprint, jsonify, request

from rag.web.context import services

logging_api = Blueprint("logging", __name__, url_prefix="/api")


def _positive_int(name, default, maximum):
    try:
        number = int(request.args.get(name, default))
    except ValueError:
        return default
    return min(number, maximum) if number > 0 else default


@logging_api.get("/generations")
def list_generations():
    conversation_id = request.args.get("conversation_id", type=int)
    page = _positive_int("page", 1, 10**6)
    per_page = _positive_int("per_page", 25, 100)
    return jsonify(services().conversations.generations(conversation_id, page, per_page))


@logging_api.get("/generations/<int:generation_id>")
def get_generation(generation_id):
    generation = services().conversations.generation(generation_id)
    if generation is None:
        return jsonify(error="Generation not found."), 404
    return jsonify(generation)


@logging_api.get("/database/tables")
def list_tables():
    return jsonify(services().database.tables())


@logging_api.get("/database/tables/<table>")
def table_rows(table):
    rows = services().database.rows(table, _positive_int("page", 1, 10**6), _positive_int("per_page", 50, 200))
    if rows is None:
        return jsonify(error="Table not found."), 404
    return jsonify(rows)
