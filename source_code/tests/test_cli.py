import os
import subprocess
import sys
from pathlib import Path

from conftest import make_pdf

from rag.web import create_app
from rag.ingestion.cli import main

ROOT = Path(__file__).resolve().parent.parent


def test_ingesting_a_folder_lists_its_documents(tmp_path, fake_ollama, capsys):
    folder = tmp_path / "dataset"
    folder.mkdir()
    make_pdf(folder / "handbook.pdf", ["The capstone project is CS499.", "Students need 128 credits."])
    storage = tmp_path / "storage"

    main([str(folder)], storage_dir=storage, ollama=fake_ollama)

    output = capsys.readouterr().out
    assert "handbook.pdf: reading pages" in output
    assert "handbook.pdf: embedding" in output
    assert "handbook.pdf: 2 chunks" in output
    client = create_app(storage_dir=storage, ollama=fake_ollama).test_client()
    documents = client.get("/api/documents").get_json()
    assert [d["name"] for d in documents] == ["handbook.pdf"]
    assert documents[0]["chunks"] > 0


def test_documents_ingested_while_the_app_is_running_are_searchable(tmp_path, fake_ollama):
    folder = tmp_path / "dataset"
    folder.mkdir()
    make_pdf(folder / "handbook.pdf", ["The capstone project is CS499.", "Students need 128 credits."])
    storage = tmp_path / "storage"
    client = create_app(storage_dir=storage, ollama=fake_ollama, min_score=0).test_client()
    conversation = client.post("/api/conversations").get_json()
    client.post(f"/api/conversations/{conversation['id']}/messages", json={"question": "Anything indexed?"})

    script = (
        "import sys; from conftest import FakeOllama; from rag.ingestion.cli import main; "
        "sys.exit(main(sys.argv[1:2], storage_dir=sys.argv[2], ollama=FakeOllama()))"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT), str(ROOT / "tests")])}
    subprocess.run([sys.executable, "-c", script, str(folder), str(storage)], check=True, env=env)

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages", json={"question": "How many credits do students need?"}
    )
    assert response.status_code == 201
    assert [c["document"] for c in response.get_json()["citations"]] == ["handbook.pdf", "handbook.pdf"]
