import json

from conftest import make_pdf

from rag.evaluation.cli import main
from rag.ingestion.cli import main as ingest


def write_questions(path, document):
    questions = [
        {"question": "How many credits do students need to graduate?", "pages": [2], "evidence": ["128 credits"]},
        {"question": "When does the cafeteria open?", "pages": [3], "evidence": ["opens at noon"]},
        {"question": "When does the library open?", "pages": [3], "evidence": ["library opens"]},
    ]
    path.write_text(json.dumps({"document": document, "questions": questions}))
    return path


def test_evaluation_reports_where_each_answer_chunk_ranks(tmp_path, fake_ollama, capsys):
    pages = [
        "1. Welcome\nWelcome to the major.",
        "2. Credits\nStudents need 128 credits to graduate.",
        "3. Cafeteria\nThe cafeteria opens at noon.",
    ]
    storage = tmp_path / "storage"
    ingest([str(make_pdf(tmp_path / "handbook.pdf", pages))], storage_dir=storage, ollama=fake_ollama)
    questions = write_questions(tmp_path / "questions.json", "handbook.pdf")
    capsys.readouterr()

    assert main([str(questions)], storage_dir=storage, ollama=fake_ollama) == 0

    output = capsys.readouterr().out
    assert " 1       1      1        1  yes/1  How many credits do students need to graduate?" in output
    # Page 3 is among the library question's candidates, but none of its text answers it.
    assert " 3       -      -        -  no/0  When does the library open?" in output
    assert "Hit@3: hybrid 2/3, dense only 2/3, keyword only 2/3" in output
    assert "Answer chunk sent to the model (top 3, score >= 0.4): 2/3" in output


def test_evaluation_needs_the_document_to_be_ingested(tmp_path, fake_ollama, capsys):
    questions = write_questions(tmp_path / "questions.json", "handbook.pdf")

    assert main([str(questions)], storage_dir=tmp_path / "storage", ollama=fake_ollama) == 1
    assert "handbook.pdf is not in the knowledge base" in capsys.readouterr().out


def test_evaluation_counts_unanswerable_questions_that_send_no_chunk(tmp_path, fake_ollama, capsys):
    pages = ["1. Welcome\nWelcome to the major.", "2. Credits\nStudents need 128 credits to graduate."]
    storage = tmp_path / "storage"
    ingest([str(make_pdf(tmp_path / "handbook.pdf", pages))], storage_dir=storage, ollama=fake_ollama)
    questions = [
        {"question": "How many credits do students need to graduate?", "pages": [2], "evidence": ["128 credits"]},
        {"question": "Who designed the logo?", "pages": [], "evidence": []},
        # Shares words with page 2, so it scores above the minimum even though page 2 doesn't answer it.
        {"question": "How many students need credits?", "pages": [], "evidence": []},
    ]
    path = tmp_path / "questions.json"
    path.write_text(json.dumps({"document": "handbook.pdf", "questions": questions}))
    capsys.readouterr()

    assert main([str(path)], storage_dir=storage, ollama=fake_ollama) == 0

    output = capsys.readouterr().out
    assert "Hit@3: hybrid 1/1" in output
    assert "Answer chunk sent to the model (top 3, score >= 0.4): 1/1" in output
    assert " 3       -      -        -  no/1  How many students need credits?" in output
    assert "Unanswerable questions with no Chunk sent to the model (score >= 0.4): 1/2" in output
