from conftest import make_pdf, upload

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


def test_chunks_are_paginated(client, tmp_path):
    upload(client, make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES))

    second_page = client.get("/api/chunks?page=2&per_page=1").get_json()

    assert second_page["total"] == 2 and second_page["page"] == 2 and second_page["per_page"] == 1
    assert [c["page"] for c in second_page["chunks"]] == [2]


def test_similarity_search_returns_chunks_above_threshold_best_first(client, tmp_path):
    upload(client, make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES))

    loose = client.post("/api/search", json={"query": "capstone project credits", "threshold": 0}).get_json()
    assert len(loose) == 2
    assert loose[0]["page"] == 2
    assert loose[0]["similarity"] > loose[1]["similarity"]
    assert all(0 <= result["similarity"] <= 1 for result in loose)

    strict = client.post(
        "/api/search", json={"query": "capstone project credits", "threshold": loose[0]["similarity"] - 0.001}
    ).get_json()
    assert [result["page"] for result in strict] == [2]

    capped = client.post("/api/search", json={"query": "capstone", "threshold": 0, "max_results": 1}).get_json()
    assert len(capped) == 1


def test_similarity_search_rejects_invalid_input(client):
    assert client.post("/api/search", json={"query": "", "threshold": 0.5}).status_code == 400
    assert client.post("/api/search", json={"query": "credits", "threshold": 1.5}).status_code == 400
    assert client.post("/api/search", json={"query": "credits", "max_results": 0}).status_code == 400


def test_similarity_search_on_empty_knowledge_base_returns_nothing(client):
    assert client.post("/api/search", json={"query": "credits"}).get_json() == []


def test_rag_page_is_served(client):
    page = client.get("/rag")

    assert page.status_code == 200
    assert b"/static/rag.js" in page.data
    assert client.get("/static/rag.js").status_code == 200
