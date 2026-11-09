from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from rag.ingestion.loader import is_supported
from rag.web.context import services

documents_api = Blueprint("documents", __name__, url_prefix="/api")


@documents_api.get("/documents")
def list_documents():
    return jsonify(services().knowledge_base.documents())


@documents_api.post("/documents")
def upload_document():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="No file uploaded."), 400
    name = secure_filename(upload.filename)
    if not is_supported(name):
        return jsonify(error="Unsupported file type. Use PDF or TXT."), 400
    path = services().uploads_dir / name
    upload.save(path)
    return jsonify(services().ingestions.start(path)), 202


@documents_api.get("/ingestions")
def list_ingestions():
    return jsonify(services().ingestions.list())


@documents_api.get("/ingestions/<job_id>")
def get_ingestion(job_id):
    job = services().ingestions.get(job_id)
    if job is None:
        return jsonify(error="Ingestion job not found."), 404
    return jsonify(job)
