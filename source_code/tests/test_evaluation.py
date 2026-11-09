import json

from conftest import make_pdf

from rag.evaluation.cli import main
from rag.ingestion.cli import main as ingest


def write_questions(path, document):
    questions = [
        {"question": "How many credits do students need to graduate?", "pages": [2]},
        {"question": "When does the cafeteria open?", "pages": [3]},
    ]
    path.write_text(json.dumps({"document": document, "questions": questions}))
    return path


def test_evaluation_reports_where_each_answer_page_ranks(tmp_path, fake_ollama, capsys):
    pages = ["Welcome to the major.", "Students need 128 credits to graduate.", "The cafeteria opens at noon."]
    storage = tmp_path / "storage"
    ingest([str(make_pdf(tmp_path / "handbook.pdf", pages))], storage_dir=storage, ollama=fake_ollama)
    questions = write_questions(tmp_path / "questions.json", "handbook.pdf")
    capsys.readouterr()

    assert main([str(questions)], storage_dir=storage, ollama=fake_ollama) == 0

    output = capsys.readouterr().out
    assert " 1       1      1        1  yes/1  How many credits do students need to graduate?" in output
    assert "Hit@3: hybrid 2/2, dense only 2/2, keyword only 2/2" in output
    assert "Answer page sent to the model (top 3, score >= 0.4): 2/2" in output


def test_evaluation_needs_the_document_to_be_ingested(tmp_path, fake_ollama, capsys):
    questions = write_questions(tmp_path / "questions.json", "handbook.pdf")

    assert main([str(questions)], storage_dir=tmp_path / "storage", ollama=fake_ollama) == 1
    assert "handbook.pdf is not in the knowledge base" in capsys.readouterr().out
