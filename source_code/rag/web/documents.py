from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from rag.ingestion.loader import is_supported
from rag.web.context import services

documents_api = Blueprint("documents", __name__, url_prefix="/api/documents")


@documents_api.get("")
def list_documents():
    return jsonify(services().knowledge_base.documents())


@documents_api.post("")
def upload_document():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="No file uploaded."), 400
    name = secure_filename(upload.filename)
    if not is_supported(name):
        return jsonify(error="Unsupported file type. Use PDF or TXT."), 400
    path = services().uploads_dir / name
    upload.save(path)
    return jsonify(services().knowledge_base.ingest(path)), 201
