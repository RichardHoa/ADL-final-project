const PER_PAGE = 50;
const PREVIEW_LENGTH = 160;

const elements = {
  searchForm: document.getElementById("search-form"),
  searchQuery: document.getElementById("search-query"),
  searchThreshold: document.getElementById("search-threshold"),
  thresholdValue: document.getElementById("threshold-value"),
  searchMax: document.getElementById("search-max"),
  searchSubmit: document.getElementById("search-submit"),
  searchStatus: document.getElementById("search-status"),
  searchError: document.getElementById("search-error"),
  searchResults: document.getElementById("search-results"),
  chunksForm: document.getElementById("chunks-form"),
  chunksDocument: document.getElementById("chunks-document"),
  chunksText: document.getElementById("chunks-text"),
  chunksError: document.getElementById("chunks-error"),
  chunksBody: document.getElementById("chunks-body"),
  chunksPrev: document.getElementById("chunks-prev"),
  chunksNext: document.getElementById("chunks-next"),
  chunksSummary: document.getElementById("chunks-summary"),
};

let chunksPage = 1;

async function request(url, options) {
  const response = await fetch(url, options);
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

function chunkText(text) {
  if (text.length <= PREVIEW_LENGTH) return element("p", "chunk-text", text);
  const details = element("details", "chunk-text");
  details.append(element("summary", "", `${text.slice(0, PREVIEW_LENGTH)}…`), element("p", "", text));
  return details;
}

function resultItem(result) {
  const item = element("li", "result");
  const header = element("div", "result__header");
  header.append(
    element("span", "score", result.similarity.toFixed(3)),
    element("span", "", `${result.document}, page ${result.page} · chunk #${result.index}`),
  );
  item.append(header, chunkText(result.text));
  return item;
}

async function search(event) {
  event.preventDefault();
  const query = elements.searchQuery.value.trim();
  if (!query) return;
  elements.searchError.textContent = "";
  elements.searchStatus.textContent = "Searching…";
  elements.searchSubmit.disabled = true;
  try {
    const threshold = Number(elements.searchThreshold.value);
    const results = await request("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, threshold, max_results: Number(elements.searchMax.value) }),
    });
    elements.searchResults.replaceChildren(...results.map(resultItem));
    elements.searchStatus.textContent = `${results.length} chunk(s) at or above similarity ${threshold.toFixed(2)}.`;
  } catch (failure) {
    elements.searchStatus.textContent = "";
    elements.searchError.textContent = failure.message;
  } finally {
    elements.searchSubmit.disabled = false;
  }
}

function chunkRow(chunk) {
  const row = element("tr");
  const text = element("td");
  text.append(chunkText(chunk.text));
  row.append(element("td", "", chunk.document), element("td", "", String(chunk.page)), element("td", "", String(chunk.index)), text);
  return row;
}

async function loadChunks() {
  elements.chunksError.textContent = "";
  const params = new URLSearchParams({
    page: chunksPage,
    per_page: PER_PAGE,
    document: elements.chunksDocument.value,
    q: elements.chunksText.value.trim(),
  });
  try {
    const { chunks, total, page } = await request(`/api/chunks?${params}`);
    const pages = Math.max(1, Math.ceil(total / PER_PAGE));
    elements.chunksBody.replaceChildren(...chunks.map(chunkRow));
    elements.chunksSummary.textContent = `${total} chunk(s) · page ${page} of ${pages}`;
    elements.chunksPrev.disabled = page <= 1;
    elements.chunksNext.disabled = page >= pages;
  } catch (failure) {
    elements.chunksError.textContent = failure.message;
  }
}

async function loadDocumentOptions() {
  const documents = await request("/api/documents");
  elements.chunksDocument.append(
    ...documents.map((doc) => {
      const option = element("option", "", `${doc.name} (${doc.chunks})`);
      option.value = doc.name;
      return option;
    }),
  );
}

function refilter() {
  chunksPage = 1;
  loadChunks();
}

let filterTimer;
elements.searchForm.addEventListener("submit", search);
elements.searchThreshold.addEventListener("input", () => {
  elements.thresholdValue.textContent = Number(elements.searchThreshold.value).toFixed(2);
});
elements.chunksForm.addEventListener("submit", (event) => event.preventDefault());
elements.chunksDocument.addEventListener("change", refilter);
elements.chunksText.addEventListener("input", () => {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(refilter, 250);
});
elements.chunksPrev.addEventListener("click", () => {
  chunksPage -= 1;
  loadChunks();
});
elements.chunksNext.addEventListener("click", () => {
  chunksPage += 1;
  loadChunks();
});

loadDocumentOptions().catch((failure) => {
  elements.chunksError.textContent = `Could not load documents: ${failure.message}`;
});
loadChunks();
