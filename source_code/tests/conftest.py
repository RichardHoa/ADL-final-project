import hashlib
import re
import time

import pytest
from fpdf import FPDF

from rag.web import create_app


class FakeOllama:
    dims = 64

    def embed(self, texts):
        vectors = []
        for text in texts:
            vector = [0.0] * self.dims
            for word in re.findall(r"\w+", text.lower()):
                index = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dims
                vector[index] += 1.0
            vectors.append(vector)
        return vectors

    def generate(self, system, prompt):
        return f"Echo: {prompt}"


def make_pdf(path, pages):
    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    for text in pages:
        pdf.add_page()
        pdf.multi_cell(0, 6, text)
    pdf.output(str(path))
    return path


def start_upload(client, path):
    with open(path, "rb") as handle:
        return client.post("/api/documents", data={"file": (handle, path.name)}, content_type="multipart/form-data")


def wait_for_job(client, job_id, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/ingestions/{job_id}").get_json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError(f"Ingestion job {job_id} did not finish")


def upload(client, path):
    return wait_for_job(client, start_upload(client, path).get_json()["id"])


@pytest.fixture
def fake_ollama():
    return FakeOllama()


@pytest.fixture
def client(tmp_path, fake_ollama):
    app = create_app(storage_dir=tmp_path / "storage", ollama=fake_ollama)
    return app.test_client()
