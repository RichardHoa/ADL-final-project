import pytest
from conftest import make_pdf, upload

from rag.retrieval.keyword import keyword_scores
from rag.web import create_app

HANDBOOK_PAGES = [
    "Welcome to the Computer Science major. The program prepares students for careers in software.",
    "Graduation requirements: students must complete 128 credits, including the capstone project CS499.",
]


def test_every_chunk_is_listed_and_can_be_filtered(client, tmp_path):
    upload(client, make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES))
    upload(client, make_pdf(tmp_path / "notes.pdf", ["Office hours are on Tuesday."]))

    listed = client.get("/api/chunks").get_json()
    assert listed["total"] == 3
    assert [(c["document"], c["page"], c["index"]) for c in listed["chunks"]] == [
        ("handbook.pdf", 1, 0),
        ("handbook.pdf", 2, 1),
        ("notes.pdf", 1, 0),
    ]

    by_document = client.get("/api/chunks?document=notes.pdf").get_json()
    assert [c["text"] for c in by_document["chunks"]] == ["Office hours are on Tuesday."]

    by_text = client.get("/api/chunks?q=capstone").get_json()
    assert [c["page"] for c in by_text["chunks"]] == [2]


def ask_and_log(client, question):
    conversation = client.post("/api/conversations").get_json()
    client.post(f"/api/conversations/{conversation['id']}/messages", json={"question": question})
    return client.get(f"/api/generations?conversation_id={conversation['id']}").get_json()["generations"]


def test_chunks_are_paginated(client, tmp_path):
    upload(client, make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES))

    second_page = client.get("/api/chunks?page=2&per_page=1").get_json()

    assert second_page["total"] == 2 and second_page["page"] == 2 and second_page["per_page"] == 1
    assert [c["page"] for c in second_page["chunks"]] == [2]


def test_search_returns_chunks_at_or_above_threshold_best_first(client, tmp_path):
    upload(client, make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES))

    loose = client.post("/api/search", json={"query": "capstone project credits", "threshold": 0}).get_json()
    assert len(loose) == 2
    assert loose[0]["page"] == 2
    assert loose[0]["score"] > loose[1]["score"]
    for result in loose:
        assert all(0 <= result[key] <= 1 for key in ("score", "similarity", "keyword"))
        assert result["score"] == pytest.approx(0.6 * result["similarity"] + 0.4 * result["keyword"])

    strict = client.post(
        "/api/search", json={"query": "capstone project credits", "threshold": loose[0]["score"] - 0.001}
    ).get_json()
    assert [result["page"] for result in strict] == [2]

    capped = client.post("/api/search", json={"query": "capstone", "threshold": 0, "max_results": 1}).get_json()
    assert len(capped) == 1


def test_chat_sends_at_most_the_top_three_chunks(client, tmp_path):
    pages = [f"Rule {number}: students must complete {number} credits of electives." for number in range(1, 6)]
    upload(client, make_pdf(tmp_path / "rules.pdf", pages))

    [generation] = ask_and_log(client, "How many credits of electives must students complete?")

    scores = [chunk["score"] for chunk in generation["chunks"]]
    assert len(scores) == 3 and scores == sorted(scores, reverse=True)


def test_chat_only_sends_chunks_scoring_at_least_the_minimum(tmp_path, fake_ollama):
    client = create_app(storage_dir=tmp_path / "storage", ollama=fake_ollama).test_client()
    upload(client, make_pdf(tmp_path / "handbook.pdf", ["Students need 128 credits to graduate.", "The cafeteria opens at noon."]))

    [credits] = ask_and_log(client, "How many credits do students need to graduate?")
    assert [chunk["page"] for chunk in credits["chunks"]] == [1]
    assert credits["chunks"][0]["score"] >= 0.4

    off_topic = ask_and_log(client, "What is the weather on Mars?")[0]
    assert off_topic["chunks"] == []
    assert off_topic["user_prompt"].startswith("Context:\n\n\nQuestion:")


def test_keyword_search_finds_course_codes_however_they_are_written():
    documents = ["CS 201 lecture", "CS201 lecture", "cafeteria menu"]

    spaced, joined, unrelated = keyword_scores("cs201", documents)

    assert spaced == joined > 0
    assert unrelated == 0


def test_keyword_score_is_the_share_of_the_query_a_chunk_covers():
    documents = ["capstone credits", "capstone hours", "office hours"]

    both, one, none = keyword_scores("capstone credits", documents)
    assert both == pytest.approx(1.0)
    assert 0 < one < both
    assert none == 0

    # A question about things no Chunk mentions can't score high on the one word it shares.
    assert keyword_scores("capstone weather forecast tomorrow", documents)[0] < 0.5


def test_search_rejects_invalid_input(client):
    assert client.post("/api/search", json={"query": "", "threshold": 0.5}).status_code == 400
    assert client.post("/api/search", json={"query": "credits", "threshold": 1.5}).status_code == 400
    assert client.post("/api/search", json={"query": "credits", "max_results": 0}).status_code == 400


def test_search_on_empty_knowledge_base_returns_nothing(client):
    assert client.post("/api/search", json={"query": "credits"}).get_json() == []


def test_rag_page_is_served(client):
    page = client.get("/rag")

    assert page.status_code == 200
    assert b"/static/rag.js" in page.data
    assert client.get("/static/rag.js").status_code == 200
