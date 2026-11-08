const elements = {
  newChat: document.getElementById("new-chat"),
  conversations: document.getElementById("conversations"),
  conversationsEmpty: document.getElementById("conversations-empty"),
  documents: document.getElementById("documents"),
  documentsEmpty: document.getElementById("documents-empty"),
  upload: document.getElementById("upload"),
  uploadStatus: document.getElementById("upload-status"),
  uploadError: document.getElementById("upload-error"),
  chatTitle: document.getElementById("chat-title"),
  messages: document.getElementById("messages"),
  chatEmpty: document.getElementById("chat-empty"),
  thinking: document.getElementById("thinking"),
  composer: document.getElementById("composer"),
  question: document.getElementById("question"),
  ask: document.getElementById("ask"),
};

let currentConversationId = null;

async function request(url, options) {
  const response = await fetch(url, options);
  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error || `Request failed (${response.status}).`);
  return body;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function chunkCount(count) {
  return `${count} ${count === 1 ? "chunk" : "chunks"}`;
}

function setHash(id) {
  history.replaceState(null, "", id === null ? location.pathname : `#${id}`);
}

async function loadConversations() {
  const conversations = await request("/api/conversations");
  elements.conversations.replaceChildren(...conversations.map(conversationItem));
  const current = conversations.find((conversation) => conversation.id === currentConversationId);
  if (current) elements.chatTitle.textContent = current.title;
  elements.conversationsEmpty.textContent = "No conversations yet.";
  elements.conversationsEmpty.hidden = conversations.length > 0;
}

function conversationItem(conversation) {
  const item = element("li", "conversation");
  if (conversation.id === currentConversationId) item.classList.add("conversation--active");

  const open = element("button", "conversation__open", conversation.title);
  open.type = "button";
  open.title = conversation.title;
  if (conversation.id === currentConversationId) open.setAttribute("aria-current", "true");
  open.addEventListener("click", () => openConversation(conversation.id));

  const remove = element("button", "conversation__delete", "Delete");
  remove.type = "button";
  remove.setAttribute("aria-label", `Delete conversation: ${conversation.title}`);
  remove.addEventListener("click", () => deleteConversation(conversation));

  item.append(open, remove);
  return item;
}

async function loadDocuments() {
  const documents = await request("/api/documents");
  elements.documents.replaceChildren(
    ...documents.map((doc) => {
      const item = element("li", "document");
      item.append(element("span", "", doc.name), element("span", "document__chunks", chunkCount(doc.chunks)));
      return item;
    }),
  );
  elements.documentsEmpty.hidden = documents.length > 0;
}

function messageItem(message) {
  const item = element("li", `message message--${message.role}`);
  item.append(
    element("span", "message__role", message.role === "user" ? "You" : "Assistant"),
    element("p", "message__content", message.content),
  );
  if (message.citations?.length) item.append(citationList(message.citations));
  return item;
}

function citationList(citations) {
  const list = element("ul", "citations");
  list.setAttribute("aria-label", "Citations");
  for (const citation of citations) {
    const details = element("details", "citation");
    details.append(
      element("summary", "citation__summary", `${citation.document}, page ${citation.page}`),
      element("blockquote", "citation__snippet", citation.snippet),
    );
    const item = element("li");
    item.append(details);
    list.append(item);
  }
  return list;
}

function errorItem(text) {
  const item = element("li", "error", text);
  item.setAttribute("role", "alert");
  return item;
}

function appendToChat(node) {
  elements.messages.append(node);
  elements.chatEmpty.hidden = true;
  node.scrollIntoView({ block: "end" });
}

function showConversation(conversation) {
  currentConversationId = conversation?.id ?? null;
  elements.chatTitle.textContent = conversation?.title ?? "New chat";
  const messages = conversation?.messages ?? [];
  elements.messages.replaceChildren(...messages.map(messageItem));
  elements.chatEmpty.hidden = messages.length > 0;
  setHash(currentConversationId);
  elements.messages.lastElementChild?.scrollIntoView({ block: "end" });
}

async function openConversation(id) {
  try {
    showConversation(await request(`/api/conversations/${id}`));
  } catch (failure) {
    showConversation(null);
    appendToChat(errorItem(failure.message));
  }
  await refreshConversations();
}

function newChat() {
  showConversation(null);
  refreshConversations();
  elements.question.focus();
}

async function deleteConversation(conversation) {
  if (!confirm(`Delete "${conversation.title}"? This cannot be undone.`)) return;
  try {
    await request(`/api/conversations/${conversation.id}`, { method: "DELETE" });
    if (conversation.id === currentConversationId) showConversation(null);
  } catch (failure) {
    appendToChat(errorItem(failure.message));
  }
  await refreshConversations();
}

async function refreshConversations() {
  try {
    await loadConversations();
  } catch (failure) {
    elements.conversationsEmpty.hidden = false;
    elements.conversationsEmpty.textContent = `Could not load conversations: ${failure.message}`;
  }
}

function setBusy(busy) {
  elements.thinking.hidden = !busy;
  elements.ask.disabled = busy;
  elements.question.readOnly = busy;
}

async function ask(event) {
  event.preventDefault();
  const question = elements.question.value.trim();
  if (!question || elements.ask.disabled) return;

  appendToChat(messageItem({ role: "user", content: question }));
  elements.question.value = "";
  setBusy(true);
  try {
    if (currentConversationId === null) {
      currentConversationId = (await request("/api/conversations", { method: "POST" })).id;
      setHash(currentConversationId);
    }
    const reply = await request(`/api/conversations/${currentConversationId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    appendToChat(messageItem(reply));
  } catch (failure) {
    appendToChat(errorItem(`${failure.message} Your question was not saved.`));
    elements.question.value = question;
  } finally {
    setBusy(false);
    elements.question.focus();
  }
  await refreshConversations();
}

async function upload() {
  const file = elements.upload.files[0];
  if (!file) return;
  elements.uploadError.textContent = "";
  elements.uploadStatus.textContent = `Ingesting ${file.name}…`;
  elements.upload.disabled = true;
  try {
    const body = new FormData();
    body.append("file", file);
    const doc = await request("/api/documents", { method: "POST", body });
    elements.uploadStatus.textContent = `Ingested ${doc.name} (${chunkCount(doc.chunks)}).`;
    await loadDocuments();
  } catch (failure) {
    elements.uploadStatus.textContent = "";
    elements.uploadError.textContent = failure.message;
  } finally {
    elements.upload.disabled = false;
    elements.upload.value = "";
  }
}

elements.newChat.addEventListener("click", newChat);
elements.composer.addEventListener("submit", ask);
elements.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});
elements.upload.addEventListener("change", upload);

async function start() {
  const id = Number.parseInt(location.hash.slice(1), 10);
  if (Number.isInteger(id)) await openConversation(id);
  else await refreshConversations();
  try {
    await loadDocuments();
  } catch (failure) {
    elements.uploadError.textContent = `Could not load documents: ${failure.message}`;
  }
}

start();
