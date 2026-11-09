from flask import Flask, jsonify

from rag.ollama_client import OllamaError
from rag.services import build_services
from rag.web.conversations import conversations_api
from rag.web.documents import documents_api
from rag.web.logging import logging_api
from rag.web.rag import rag_api


def create_app(storage_dir=None, ollama=None, top_k=None, min_score=None):
    app = Flask(__name__)
    app.extensions["rag"] = build_services(storage_dir, ollama, top_k, min_score)
    app.register_blueprint(documents_api)
    app.register_blueprint(conversations_api)
    app.register_blueprint(rag_api)
    app.register_blueprint(logging_api)

    @app.errorhandler(OllamaError)
    def ollama_unreachable(error):
        return jsonify(error=str(error)), 502

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/rag")
    def rag_page():
        return app.send_static_file("rag.html")

    @app.get("/logging")
    def logging_page():
        return app.send_static_file("logging.html")

    return app
