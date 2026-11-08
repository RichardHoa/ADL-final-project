from flask import Flask, jsonify

from rag.ollama_client import OllamaError
from rag.services import build_services
from rag.web.conversations import conversations_api
from rag.web.documents import documents_api


def create_app(storage_dir=None, ollama=None, top_k=None):
    app = Flask(__name__)
    app.extensions["rag"] = build_services(storage_dir, ollama, top_k)
    app.register_blueprint(documents_api)
    app.register_blueprint(conversations_api)

    @app.errorhandler(OllamaError)
    def ollama_unreachable(error):
        return jsonify(error=str(error)), 502

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    return app
