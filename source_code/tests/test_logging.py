from conftest import FakeOllama, make_pdf, upload

from rag.ollama_client import OllamaError
from rag.web import create_app

HANDBOOK_PAGES = [
    "Welcome to the Computer Science major. The program prepares students for careers in software.",
    "Graduation requirements: students must complete 128 credits, including the capstone project CS499.",
]


class BrokenModel(FakeOllama):
    def generate(self, system, prompt):
        raise OllamaError("Could not reach Ollama: model crashed")


def ask(client, conversation_id, question):
    return client.post(f"/api/conversations/{conversation_id}/messages", json={"question": question})


def test_each_answer_records_its_generation(client, tmp_path):
    upload(client, make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES))
    conversation = client.post("/api/conversations").get_json()

    answer = ask(client, conversation["id"], "How many credits are required?").get_json()

    listed = client.get("/api/generations").get_json()
    assert listed["total"] == 1
    generation = listed["generations"][0]
    assert generation["id"] == answer["generation_id"]
    assert generation["status"] == "ok"
    assert generation["conversation_id"] == conversation["id"]
    assert generation["conversation_title"] == "How many credits are required?"
    assert generation["message_id"] == answer["id"]
    assert generation["question"] == "How many credits are required?"
    assert "Answer only from the provided context" in generation["system_prompt"]
    assert "128 credits" in generation["user_prompt"]
    assert generation["user_prompt"].endswith("Question: How many credits are required?\nAnswer:")
    assert generation["answer"] == answer["content"]
    assert generation["model"] == "qwen2.5:0.5b"
    assert generation["duration_ms"] >= 0
    assert {(c["document"], c["page"]) for c in generation["chunks"]} == {("handbook.pdf", 1), ("handbook.pdf", 2)}
    assert all(0 <= c["similarity"] <= 1 for c in generation["chunks"])

    assert client.get(f"/api/generations/{generation['id']}").get_json() == generation
    reloaded = client.get(f"/api/conversations/{conversation['id']}").get_json()
    assert reloaded["messages"][1]["generation_id"] == generation["id"]
    assert reloaded["messages"][0]["generation_id"] is None


def test_failed_generation_is_recorded_without_saving_messages(tmp_path):
    client = create_app(storage_dir=tmp_path / "storage", ollama=BrokenModel(), min_score=0).test_client()
    upload(client, make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES))
    conversation = client.post("/api/conversations").get_json()

    response = ask(client, conversation["id"], "How many credits are required?")

    assert response.status_code == 502
    assert client.get(f"/api/conversations/{conversation['id']}").get_json()["messages"] == []
    [generation] = client.get("/api/generations").get_json()["generations"]
    assert generation["status"] == "error"
    assert "model crashed" in generation["error"]
    assert generation["message_id"] is None and generation["answer"] is None
    assert "128 credits" in generation["user_prompt"]


def test_generations_are_newest_first_filterable_and_deleted_with_their_conversation(client):
    first = client.post("/api/conversations").get_json()
    second = client.post("/api/conversations").get_json()
    ask(client, first["id"], "One?")
    ask(client, second["id"], "Two?")
    ask(client, first["id"], "Three?")

    listed = client.get("/api/generations").get_json()
    assert [g["question"] for g in listed["generations"]] == ["Three?", "Two?", "One?"]

    paged = client.get("/api/generations?page=2&per_page=2").get_json()
    assert [g["question"] for g in paged["generations"]] == ["One?"] and paged["total"] == 3

    filtered = client.get(f"/api/generations?conversation_id={first['id']}").get_json()
    assert [g["question"] for g in filtered["generations"]] == ["Three?", "One?"]

    client.delete(f"/api/conversations/{first['id']}")
    assert [g["question"] for g in client.get("/api/generations").get_json()["generations"]] == ["Two?"]


def test_unknown_generation_is_not_found(client):
    assert client.get("/api/generations/999").status_code == 404


def test_chat_database_tables_can_be_browsed_read_only(client):
    conversation = client.post("/api/conversations").get_json()
    ask(client, conversation["id"], "One?")
    ask(client, conversation["id"], "Two?")

    tables = {t["name"]: t["rows"] for t in client.get("/api/database/tables").get_json()}
    assert tables == {"conversations": 1, "messages": 4, "generations": 2}

    page = client.get("/api/database/tables/messages?page=2&per_page=3").get_json()
    assert page["total"] == 4 and page["page"] == 2
    assert "content" in page["columns"] and "role" in page["columns"]
    assert len(page["rows"]) == 1
    assert len(page["rows"][0]) == len(page["columns"])

    assert client.get("/api/database/tables/sqlite_sequence").status_code == 404
    assert client.get("/api/database/tables/messages;DROP TABLE messages").status_code == 404


def test_logging_page_is_served(client):
    page = client.get("/logging")

    assert page.status_code == 200
    assert b"/static/logging.js" in page.data
    assert client.get("/static/logging.js").status_code == 200
