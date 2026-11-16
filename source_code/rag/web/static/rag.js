const PER_PAGE = 50;

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

// Chunks list every page they span, and the pages are always consecutive.
function pageRange({ pages }) {
  return pages.length === 1 ? String(pages[0]) : `${pages[0]}–${pages.at(-1)}`;
}

function pageLabel(chunk) {
  return `${chunk.pages.length === 1 ? "page" : "pages"} ${pageRange(chunk)}`;
}

// Chunks ingested before heading and part were recorded have neither, so their text is shown as stored.
function hasParts(chunk) {
  return typeof chunk.heading === "string" && Number.isInteger(chunk.part);
}

function partLabel(chunk) {
  return chunk.parts === 1 ? "Whole section" : `Part ${chunk.part} of ${chunk.parts}`;
}

function headingTrail(heading) {
  const trail = element("p", "chunk__heading");
  if (!heading) {
    trail.append(element("span", "chunk__crumb chunk__crumb--none", "Before the first heading"));
    return trail;
  }
  heading.split(" > ").forEach((title, position) => {
    if (position > 0) trail.append(element("span", "chunk__separator", "›"));
    trail.append(element("span", "chunk__crumb", title));
  });
  return trail;
}

// A Chunk's text is its heading path, a newline, then the section's text: the heading is shown apart from the body.
function chunkBlock(chunk) {
  const block = element("div", "chunk");
  let body = chunk.text;
  if (hasParts(chunk)) {
    const meta = element("div", "chunk__meta");
    meta.append(element("span", `part part--${chunk.parts === 1 ? "whole" : "split"}`, partLabel(chunk)), headingTrail(chunk.heading));
    block.append(meta);
    if (chunk.heading) body = chunk.text.slice(chunk.heading.length + 1);
  }
  const text = element("p", "chunk__body", body);
  const toggle = element("button", "chunk__toggle", "Show full text");
  toggle.type = "button";
  toggle.hidden = true;
  toggle.setAttribute("aria-expanded", "false");
  toggle.addEventListener("click", () => {
    const expanded = text.classList.toggle("chunk__body--expanded");
    toggle.setAttribute("aria-expanded", String(expanded));
    toggle.textContent = expanded ? "Show less" : "Show full text";
  });
  block.append(text, toggle);
  return block;
}

// Bodies are clamped to a few lines; only the ones actually cut off get a toggle.
function revealToggles(container) {
  for (const block of container.querySelectorAll(".chunk")) {
    const body = block.querySelector(".chunk__body");
    if (body.classList.contains("chunk__body--expanded")) continue;
    block.querySelector(".chunk__toggle").hidden = body.scrollHeight <= body.clientHeight + 1;
  }
}

function scoreParts(result) {
  return [
    element("span", "score", result.score.toFixed(3)),
    element("span", "", `dense ${result.similarity.toFixed(3)} · keyword ${result.keyword.toFixed(3)}`),
  ];
}

function resultItem(result) {
  const item = element("li", "result");
  const header = element("div", "result__header");
  header.append(
    ...scoreParts(result),
    element("span", "", `${result.document}, ${pageLabel(result)} · chunk #${result.index}`),
  );
  item.append(header, chunkBlock(result));
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
    revealToggles(elements.searchResults);
    elements.searchStatus.textContent = `${results.length} chunk(s) at or above score ${threshold.toFixed(2)}.`;
  } catch (failure) {
    elements.searchStatus.textContent = "";
    elements.searchError.textContent = failure.message;
  } finally {
    elements.searchSubmit.disabled = false;
  }
}

// Parts of one long section that sit in adjacent rows are joined by a rail through their numbers.
function follows(chunk, previous) {
  return Boolean(chunk && previous) && hasParts(chunk) && chunk.part > 1 && previous.document === chunk.document && previous.index === chunk.index - 1;
}

function chunkRow(chunk, position, chunks) {
  const row = element("tr", "chunk-row");
  row.classList.toggle("chunk-row--joins-previous", follows(chunk, chunks[position - 1]));
  row.classList.toggle("chunk-row--joins-next", follows(chunks[position + 1], chunk));
  const number = element("td", "chunk-row__index");
  number.append(element("span", `index index--${!hasParts(chunk) ? "unknown" : chunk.parts === 1 ? "whole" : "split"}`, String(chunk.index)));
  const text = element("td");
  text.append(chunkBlock(chunk));
  row.append(number, element("td", "", chunk.document), element("td", "chunk-row__pages", pageRange(chunk)), text);
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
    revealToggles(elements.chunksBody);
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
let resizeTimer;
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
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    revealToggles(elements.searchResults);
    revealToggles(elements.chunksBody);
  }, 150);
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
