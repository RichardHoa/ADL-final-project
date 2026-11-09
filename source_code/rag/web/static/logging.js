const GENERATIONS_PER_PAGE = 25;
const ROWS_PER_PAGE = 50;
const CELL_PREVIEW_LENGTH = 120;

const elements = {
  tabs: [...document.querySelectorAll(".tab")],
  generationsForm: document.getElementById("generations-form"),
  generationsConversation: document.getElementById("generations-conversation"),
  generationsError: document.getElementById("generations-error"),
  generations: document.getElementById("generations"),
  generationsEmpty: document.getElementById("generations-empty"),
  generationsPrev: document.getElementById("generations-prev"),
  generationsNext: document.getElementById("generations-next"),
  generationsSummary: document.getElementById("generations-summary"),
  databaseForm: document.getElementById("database-form"),
  databaseTable: document.getElementById("database-table"),
  databaseError: document.getElementById("database-error"),
  databaseHead: document.getElementById("database-head"),
  databaseBody: document.getElementById("database-body"),
  databasePrev: document.getElementById("database-prev"),
  databaseNext: document.getElementById("database-next"),
  databaseSummary: document.getElementById("database-summary"),
};

let generationsPage = 1;
let databasePage = 1;

async function request(url) {
  const response = await fetch(url);
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error || `Request failed (${response.status}).`);
  return body;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatTime(iso) {
  return new Date(iso).toLocaleString();
}

function block(title, text) {
  const section = element("section", "generation__block");
  section.append(element("h3", "generation__label", title), element("pre", "code", text ?? "—"));
  return section;
}

function chunksBlock(chunks) {
  const section = element("section", "generation__block");
  section.append(element("h3", "generation__label", `Retrieved chunks (${chunks.length})`));
  const list = element("ol", "results");
  for (const chunk of chunks) {
    const item = element("li", "result");
    const header = element("div", "result__header");
    header.append(
      element("span", "score", chunk.similarity.toFixed(3)),
      element("span", "", `${chunk.document}, page ${chunk.page} · chunk #${chunk.index}`),
    );
    item.append(header, element("p", "chunk-text", chunk.text));
    list.append(item);
  }
  section.append(list);
  return section;
}

function generationItem(generation) {
  const item = element("li");
  const details = element("details", "generation");
  details.id = `generation-${generation.id}`;
  const summary = element("summary", "generation__summary");
  const badge = element("span", `badge badge--${generation.status}`, generation.status);
  summary.append(
    badge,
    element("span", "generation__question", generation.question),
    element("span", "hint", `${generation.conversation_title} · ${formatTime(generation.created_at)} · ${(generation.duration_ms / 1000).toFixed(1)} s`),
  );
  const body = element("div", "generation__body");
  body.append(element("p", "hint", `Model: ${generation.model} · Generation #${generation.id}`));
  if (generation.error) body.append(element("p", "error", generation.error));
  body.append(
    chunksBlock(generation.chunks),
    block("System prompt", generation.system_prompt),
    block("User prompt", generation.user_prompt),
    block("Raw answer", generation.answer),
  );
  details.append(summary, body);
  item.append(details);
  return item;
}

async function loadGenerations() {
  elements.generationsError.textContent = "";
  const params = new URLSearchParams({ page: generationsPage, per_page: GENERATIONS_PER_PAGE });
  if (elements.generationsConversation.value) params.set("conversation_id", elements.generationsConversation.value);
  try {
    const { generations, total, page } = await request(`/api/generations?${params}`);
    const pages = Math.max(1, Math.ceil(total / GENERATIONS_PER_PAGE));
    elements.generations.replaceChildren(...generations.map(generationItem));
    elements.generationsEmpty.hidden = total > 0;
    elements.generationsSummary.textContent = `${total} Generation(s) · page ${page} of ${pages}`;
    elements.generationsPrev.disabled = page <= 1;
    elements.generationsNext.disabled = page >= pages;
  } catch (failure) {
    elements.generationsError.textContent = failure.message;
  }
}

async function loadConversationOptions() {
  const selected = elements.generationsConversation.value;
  const conversations = await request("/api/conversations");
  const all = element("option", "", "All conversations");
  all.value = "";
  elements.generationsConversation.replaceChildren(
    all,
    ...conversations.map((conversation) => {
      const option = element("option", "", conversation.title);
      option.value = conversation.id;
      return option;
    }),
  );
  elements.generationsConversation.value = selected;
}

async function showLinkedGeneration(id) {
  try {
    const generation = await request(`/api/generations/${id}`);
    let item = document.getElementById(`generation-${id}`);
    if (!item) {
      elements.generations.prepend(generationItem(generation));
      item = document.getElementById(`generation-${id}`);
    }
    item.open = true;
    item.scrollIntoView({ block: "start" });
  } catch (failure) {
    elements.generationsError.textContent = failure.message;
  }
}

function cell(value) {
  const td = element("td");
  if (value === null) {
    td.append(element("span", "hint", "NULL"));
    return td;
  }
  const text = String(value);
  if (text.length <= CELL_PREVIEW_LENGTH) {
    td.textContent = text;
    return td;
  }
  const details = element("details", "chunk-text");
  details.append(element("summary", "", `${text.slice(0, CELL_PREVIEW_LENGTH)}…`), element("pre", "code", text));
  td.append(details);
  return td;
}

async function loadTables() {
  const selected = elements.databaseTable.value;
  const tables = await request("/api/database/tables");
  elements.databaseTable.replaceChildren(
    ...tables.map((table) => {
      const option = element("option", "", `${table.name} (${table.rows})`);
      option.value = table.name;
      return option;
    }),
  );
  if (selected) elements.databaseTable.value = selected;
}

async function loadRows() {
  elements.databaseError.textContent = "";
  const table = elements.databaseTable.value;
  if (!table) return;
  try {
    const params = new URLSearchParams({ page: databasePage, per_page: ROWS_PER_PAGE });
    const { columns, rows, total, page } = await request(`/api/database/tables/${encodeURIComponent(table)}?${params}`);
    const pages = Math.max(1, Math.ceil(total / ROWS_PER_PAGE));
    elements.databaseHead.replaceChildren(
      ...columns.map((column) => {
        const th = element("th", "", column);
        th.scope = "col";
        return th;
      }),
    );
    elements.databaseBody.replaceChildren(
      ...rows.map((values) => {
        const tr = element("tr");
        tr.append(...values.map(cell));
        return tr;
      }),
    );
    elements.databaseSummary.textContent = `${total} row(s) · page ${page} of ${pages}`;
    elements.databasePrev.disabled = page <= 1;
    elements.databaseNext.disabled = page >= pages;
  } catch (failure) {
    elements.databaseError.textContent = failure.message;
  }
}

async function refreshDatabase() {
  try {
    await loadTables();
    await loadRows();
  } catch (failure) {
    elements.databaseError.textContent = failure.message;
  }
}

function selectTab(tab) {
  for (const other of elements.tabs) {
    const selected = other === tab;
    other.setAttribute("aria-selected", String(selected));
    other.tabIndex = selected ? 0 : -1;
    document.getElementById(other.getAttribute("aria-controls")).hidden = !selected;
  }
  if (tab.id === "tab-database") refreshDatabase();
}

elements.tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", (event) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    const next = elements.tabs[(index + step + elements.tabs.length) % elements.tabs.length];
    selectTab(next);
    next.focus();
  });
});
elements.generationsForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadConversationOptions().catch(() => {});
  loadGenerations();
});
elements.generationsConversation.addEventListener("change", () => {
  generationsPage = 1;
  loadGenerations();
});
elements.generationsPrev.addEventListener("click", () => {
  generationsPage -= 1;
  loadGenerations();
});
elements.generationsNext.addEventListener("click", () => {
  generationsPage += 1;
  loadGenerations();
});
elements.databaseForm.addEventListener("submit", (event) => {
  event.preventDefault();
  refreshDatabase();
});
elements.databaseTable.addEventListener("change", () => {
  databasePage = 1;
  loadRows();
});
elements.databasePrev.addEventListener("click", () => {
  databasePage -= 1;
  loadRows();
});
elements.databaseNext.addEventListener("click", () => {
  databasePage += 1;
  loadRows();
});

async function start() {
  loadConversationOptions().catch((failure) => {
    elements.generationsError.textContent = `Could not load conversations: ${failure.message}`;
  });
  await loadGenerations();
  const linked = new URLSearchParams(location.search).get("generation");
  if (linked) await showLinkedGeneration(linked);
}

start();
