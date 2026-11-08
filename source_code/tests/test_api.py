from conftest import make_pdf


HANDBOOK_PAGES = [
    "Welcome to the Computer Science major. The program prepares students for careers in software.",
    "Graduation requirements: students must complete 128 credits, including the capstone project CS499.",
]


def upload(client, path):
    with open(path, "rb") as handle:
        return client.post("/api/documents", data={"file": (handle, path.name)}, content_type="multipart/form-data")


def test_uploaded_pdf_is_listed_with_chunks(client, tmp_path):
    pdf = make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES)

    response = upload(client, pdf)

    assert response.status_code == 201
    documents = client.get("/api/documents").get_json()
    assert [d["name"] for d in documents] == ["handbook.pdf"]
    assert documents[0]["chunks"] > 0


def test_question_is_answered_with_citations_and_conversation_reloads(client, tmp_path):
    upload(client, make_pdf(tmp_path / "handbook.pdf", HANDBOOK_PAGES))
    conversation = client.post("/api/conversations").get_json()

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"question": "How many credits are required for graduation?"},
    )

    assert response.status_code == 201
    answer = response.get_json()
    assert answer["role"] == "assistant"
    assert "128 credits" in answer["content"]
    assert {"document": "handbook.pdf", "page": 2} in [
        {"document": c["document"], "page": c["page"]} for c in answer["citations"]
    ]
    assert all(c["snippet"] for c in answer["citations"])

    listed = client.get("/api/conversations").get_json()
    assert [c["title"] for c in listed] == ["How many credits are required for graduation?"]

    reloaded = client.get(f"/api/conversations/{conversation['id']}").get_json()
    assert [m["role"] for m in reloaded["messages"]] == ["user", "assistant"]
    assert reloaded["messages"][0]["content"] == "How many credits are required for graduation?"
    assert reloaded["messages"][1]["citations"] == answer["citations"]


def test_conversations_are_listed_most_recently_active_first_and_can_be_deleted(client):
    first = client.post("/api/conversations").get_json()
    second = client.post("/api/conversations").get_json()
    client.post(f"/api/conversations/{first['id']}/messages", json={"question": "What is the capstone?"})

    listed = client.get("/api/conversations").get_json()
    assert [c["id"] for c in listed] == [first["id"], second["id"]]

    assert client.delete(f"/api/conversations/{first['id']}").status_code == 204
    assert [c["id"] for c in client.get("/api/conversations").get_json()] == [second["id"]]
    assert client.get(f"/api/conversations/{first['id']}").status_code == 404


def test_chat_page_and_its_assets_are_served(client):
    page = client.get("/")

    assert page.status_code == 200
    assert b"/static/app.js" in page.data and b"/static/app.css" in page.data
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/app.css").status_code == 200
