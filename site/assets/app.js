// /try/ page: read a letter on the device, let the person check the words, call /api/check then /api/explain,
// render the results. The photo itself never leaves the browser; only the reviewed text is sent.

import { h, scrollToEl } from "./js/dom.js";
import { todayIso } from "./js/dates.js";
import { prepareFile, UserFacingError } from "./js/prepare.js";
import { postJson, getSample, ApiError } from "./js/api.js";
import { renderCheck, renderProgress, renderExplanation } from "./js/render.js";

const $ = (sel) => document.querySelector(sel);
const form = $("#check-form");
// The result sheet is not a live region (a screen reader would read all of it twice, once as it appears and
// again when focus moves there). Only a short status line is announced.
const resultsRegion = $("#results");
const results = $("#results-body");
const resultsStatus = $("#results-status");
const textInput = $("#text-input");
const textLabel = $("#text-label");
const textHint = $("#text-hint");
const languageSelect = $("#language");
const ocrLangSelect = $("#ocr-lang");
const formError = $("#form-error");
const submitBtn = $("#submit-btn");
const chosen = $("#chosen");
const readLive = $("#read-live");
const dropzone = $("#dropzone");

const PREFS_KEY = "plainly.prefs";
const LANGUAGE_NAMES = { English: "English", Hindi: "हिन्दी", Spanish: "Español" };
const TEXT_HINT_PASTE = textHint.textContent;
const LOW_CONFIDENCE = 70; // Tesseract's mean word confidence, 0-100

// The chosen file: { file, prepared, previewUrl, status: "preparing"|"reading"|"done"|"failed", langs, ms, seq }.
let letter = null;
// Where the text in the box came from: "typed", "device_ocr" or "pdf_text". Small edits (fixing misread words)
// keep the source; emptying the box, or replacing most of its words, makes it "typed" again.
let textSource = "typed";
// The text the device read, as it was put in the box (to tell a correction from a replacement).
let filledText = "";
// Length of the box at the last input event, to spot a big paste or deletion.
let lastLength = 0;
// The last check shown, used by "explain in another language".
let current = null;
// Bumped whenever the results area moves on (new check, sample, start over), so a slow /api/check answer
// can't replace what is on screen now.
let viewSeq = 0;
// Bumped whenever the explanation slot moves on, so only the newest /api/explain answer is shown.
let explainSeq = 0;
// Bumped whenever the chosen file changes or its reading is cancelled.
let readSeq = 0;
// The OCR module, imported only when a photo or scanned PDF needs reading.
let ocrModule = null;

// ---------- preferences ----------

function loadPrefs() {
  let prefs = {};
  try {
    prefs = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}");
  } catch {
    // Private mode or corrupted value: fall back to defaults.
  }
  const browser = (navigator.language || "").slice(0, 2);
  const language = prefs.language || { hi: "Hindi", es: "Spanish" }[browser] || "English";
  languageSelect.value = LANGUAGE_NAMES[language] ? language : "English";
  ocrLangSelect.value = prefs.ocrLangs === "eng+hin" || (!prefs.ocrLangs && (browser === "hi" || language === "Hindi"))
    ? "eng+hin" : "eng";
  if (prefs.level === "normal") $("#level-normal").checked = true;
}

function savePrefs() {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify({
      language: chosenLanguage(), level: chosenLevel(), ocrLangs: ocrLangSelect.value,
    }));
  } catch {
    // Storage can be unavailable; preferences are a convenience only.
  }
}

function chosenLanguage() {
  return LANGUAGE_NAMES[languageSelect.value] ? languageSelect.value : "English";
}

function chosenLevel() {
  return form.elements.level.value === "normal" ? "normal" : "simple";
}

// ---------- choosing a file ----------

function setFile(file) {
  clearFile();
  hideFormError();
  const seq = ++readSeq;
  letter = { file, prepared: null, previewUrl: null, status: "preparing", langs: null, ms: null, seq };
  showChosen();
  prepareFile(file).then((prepared) => {
    if (seq !== readSeq) return revoke(prepared.preview);
    letter.prepared = prepared;
    letter.previewUrl = prepared.preview;
    if (prepared.kind === "pdf_text") {
      letter.status = "done";
      finishReading(letter, prepared.text, "pdf_text");
    } else {
      readLetter();
    }
  }, (err) => {
    if (seq !== readSeq) return;
    letter.status = "failed";
    letter.error = err instanceof UserFacingError ? err.message : "We couldn't open that file. Try a photo or a PDF.";
    showChosen();
  });
}

async function readLetter() {
  const seq = ++readSeq;
  const entry = letter;
  entry.seq = seq;
  entry.status = "reading";
  entry.langs = ocrLangSelect.value;
  entry.progress = { fraction: 0, phase: "load", page: 1, pages: entry.prepared.images.length };
  entry.readText = null;
  showChosen();
  announceRead("Reading the letter on your device. This can take up to a minute.");
  try {
    ocrModule ??= await import("./js/ocr.js");
  } catch {
    if (seq !== readSeq) return;
    return readFailed(entry, "We couldn't load the reader. Check your connection, or type or paste the letter's words below.");
  }
  try {
    const out = await ocrModule.recognize(entry.prepared.images, entry.langs, (p) => {
      if (seq !== readSeq) return;
      entry.progress = p;
      updateProgress(entry);
    });
    if (seq !== readSeq) return;
    if (out.text.replace(/\s/g, "").length < 10) {
      return readFailed(entry, "We couldn't find any words in this picture. Try a clearer, closer photo in good light, or type or paste the words below.");
    }
    entry.status = "done";
    entry.ms = out.ms;
    entry.confidence = out.confidence;
    finishReading(entry, out.text, "device_ocr");
  } catch (err) {
    if (seq !== readSeq || err?.name === "OcrCancelled") return;
    readFailed(entry, "We couldn't read this letter on your device. Type or paste its words below instead. "
      + "(Older browsers, such as Safari before iOS 16, can't run the reader.)");
  }
}

// Puts what the device read in the box, unless the person has already typed or pasted something there: then
// their text stays, and a button offers to replace it.
function finishReading(entry, text, source) {
  const typed = textSource === "typed" && textInput.value.trim();
  if (typed) {
    entry.readText = text;
    entry.readSource = source;
  } else {
    fillText(text, source);
  }
  const keepFocus = focusIsInChosen();
  showChosen();
  if (typed) {
    announceRead("Reading finished. The box still has the text you typed; use the button to replace it with the words read from the letter.");
    if (keepFocus) chosen.querySelector("[data-focus]")?.focus();
  } else {
    announceRead("Reading finished. Check the words in the box, then press Check this letter.");
    if (keepFocus) textInput.focus({ preventScroll: true });
  }
}

function useReadText() {
  if (!letter?.readText) return;
  fillText(letter.readText, letter.readSource || "device_ocr");
  letter.readText = null;
  showChosen();
  announceRead("The box now has the words read from the letter. Check them, then press Check this letter.");
  textInput.focus({ preventScroll: true });
}

function readFailed(entry, message) {
  entry.status = "failed";
  entry.error = message;
  showChosen();
  announceRead(message);
  textInput.focus({ preventScroll: true });
}

function cancelReading() {
  readSeq++;
  ocrModule?.cancelOcr();
  if (letter) {
    letter.status = "cancelled";
    showChosen();
    announceRead("Reading stopped. Read it again, or type or paste the words in the box.");
    chosen.querySelector("[data-focus]")?.focus();
  }
}

function announceRead(message) {
  readLive.textContent = "";
  setTimeout(() => { readLive.textContent = message; }, 50);
}

function focusIsInChosen() {
  const active = document.activeElement;
  return !active || active === document.body || chosen.contains(active);
}

function fillText(text, source) {
  textInput.value = text.slice(0, Number(textInput.maxLength) || 30000);
  textSource = source;
  filledText = textInput.value;
  lastLength = filledText.length;
  syncTextLabel();
}

function syncTextLabel() {
  const fromLetter = textSource !== "typed";
  textLabel.textContent = fromLetter ? "Check the words we read" : "Or paste the text";
  textHint.textContent = fromLetter
    ? "Check the text matches your letter; fix anything misread. This is exactly what will be checked."
    : TEXT_HINT_PASTE;
  textInput.classList.toggle("from-letter", fromLetter);
}

function describeFile(entry) {
  const p = entry.prepared;
  if (!p?.pages) return null;
  const range = p.pages === 1 ? "page 1" : `pages 1 to ${p.pages}`;
  return `PDF: ${range}${p.totalPages > p.pages ? ` of ${p.totalPages}` : ""}.`;
}

function showChosen() {
  const entry = letter;
  chosen.hidden = !entry;
  if (!entry) return chosen.replaceChildren();
  const removeBtn = h("button", { type: "button", class: "btn btn-quiet btn-small", onclick: removeFile }, "Remove");
  const thumb = entry.previewUrl
    ? h("img", { src: entry.previewUrl, alt: "Preview of the letter you chose" })
    : h("span", { class: "chosen-blank", "aria-hidden": "true" });
  const lines = [h("p", null, h("strong", null, entry.file.name))];
  const pdfLine = describeFile(entry);
  let extra = null;

  if (entry.status === "preparing") {
    lines.push(h("p", { class: "muted small" }, "Opening the file…"));
  } else if (entry.status === "reading") {
    const bar = h("progress", { max: 100, value: 0, "aria-labelledby": "read-status" });
    const pct = h("span", { class: "read-pct" }, "0%");
    const stage = h("span", { class: "muted small", id: "read-stage" });
    extra = h("div", { class: "reading" },
      h("p", { class: "read-status", id: "read-status" }, "Reading on your device… ", pct),
      bar,
      h("div", { class: "reading-foot" }, stage,
        h("button", { type: "button", class: "btn btn-quiet btn-small", onclick: cancelReading, "data-focus": "" }, "Cancel")));
    entry.ui = { bar, pct, stage };
    updateProgress(entry);
  } else if (entry.status === "done") {
    const how = entry.prepared.kind === "pdf_text"
      ? "Text taken from the PDF itself, no reading needed."
      : `Read on your device in ${(entry.ms / 1000).toFixed(1)} s. The ${entry.prepared.pages ? "PDF" : "photo"} was not uploaded.`;
    lines.push(h("p", { class: "muted small" }, [pdfLine, how].filter(Boolean).join(" ")));
    if (entry.confidence != null && entry.confidence < LOW_CONFIDENCE) {
      lines.push(h("p", { class: "small warn-line" }, "Some words were hard to read. Compare the text below with your letter carefully."));
    }
    if (entry.readText) {
      lines.push(h("p", { class: "small warn-line" }, "The box below still has the text you typed, so we didn't replace it."));
    }
  } else if (entry.status === "cancelled") {
    lines.push(h("p", { class: "muted small" }, "Reading stopped. Read it again, or type or paste the words below."));
  } else if (entry.status === "failed") {
    lines.push(h("p", { class: "small warn-line" }, entry.error));
  }

  const canReread = entry.prepared?.images && (entry.status === "cancelled"
    || entry.status === "failed" || (entry.status === "done" && entry.langs !== ocrLangSelect.value));
  const actions = entry.status === "reading" ? null : h("div", { class: "btn-row" },
    entry.status === "done" && entry.readText
      ? h("button", { type: "button", class: "btn btn-small", onclick: useReadText, "data-focus": "" },
        "Use the words read from the letter") : null,
    canReread ? h("button", { type: "button", class: "btn btn-small", onclick: readLetter,
      "data-focus": entry.readText ? null : "" },
    entry.status === "done" ? "Read again in this language" : "Read it again") : null,
    removeBtn);

  // Replacing the buttons would drop keyboard focus to the top of the page; move it to the new main button.
  const hadFocus = chosen.contains(document.activeElement);
  chosen.replaceChildren(h("div", { class: "chosen" }, thumb, h("div", null, ...lines),
    extra || actions ? h("div", { class: "chosen-wide" }, extra, actions) : null));
  if (hadFocus) (chosen.querySelector("[data-focus]") || removeBtn).focus({ preventScroll: true });
}

function updateProgress(entry) {
  const ui = entry.ui;
  const p = entry.progress;
  if (!ui || !p) return;
  const percent = Math.round(p.fraction * 100);
  ui.bar.value = percent;
  ui.pct.textContent = `${percent}%`;
  ui.stage.textContent = p.phase === "load"
    ? "Getting the reader ready. The first time, your browser downloads it (about 7 MB, 8.5 MB with Hindi); after that it starts quickly."
    : p.pages > 1 ? `Page ${p.page} of ${p.pages}` : "Reading the words";
}

function revoke(url) {
  if (url) URL.revokeObjectURL(url);
}

function clearFile() {
  if (letter?.status === "reading") ocrModule?.cancelOcr();
  readSeq++;
  revoke(letter?.previewUrl);
  letter = null;
  showChosen();
  $("#file-input").value = "";
  $("#camera-input").value = "";
}

function removeFile() {
  clearFile();
  if (textSource !== "typed") {
    textInput.value = "";
    textSource = "typed";
    syncTextLabel();
  }
  $("#file-input").focus();
}

for (const input of [$("#file-input"), $("#camera-input")]) {
  input.addEventListener("change", () => input.files[0] && setFile(input.files[0]));
}

for (const type of ["dragenter", "dragover"]) {
  dropzone.addEventListener(type, (e) => {
    e.preventDefault();
    dropzone.classList.add("is-over");
  });
}
for (const type of ["dragleave", "drop"]) {
  dropzone.addEventListener(type, () => dropzone.classList.remove("is-over"));
}
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  const file = e.dataTransfer?.files?.[0];
  if (file) setFile(file);
});
// A file dropped outside the zone would otherwise navigate away from the page.
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => e.preventDefault());

// Words in a text, for telling a correction from a replacement.
function wordsOf(text) {
  return text.toLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
}

textInput.addEventListener("input", () => {
  const value = textInput.value;
  const jump = Math.abs(value.length - lastLength);
  lastLength = value.length;
  if (textSource === "typed") return;
  let replaced = !value.trim();
  if (!replaced && jump > 20) {
    // A big paste or deletion: if most of the words are no longer the ones the device read, the text is the
    // person's own now, and the receipts must not say the device read it.
    const read = new Set(wordsOf(filledText));
    const words = wordsOf(value);
    const kept = words.filter((w) => read.has(w)).length;
    replaced = words.length >= 5 && kept < words.length * 0.5;
  }
  if (replaced) {
    textSource = "typed";
    filledText = "";
    syncTextLabel();
  }
});

ocrLangSelect.addEventListener("change", () => {
  savePrefs();
  if (letter && letter.status !== "reading") showChosen();
});

// ---------- form errors ----------

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function hideFormError() {
  formError.hidden = true;
  formError.textContent = "";
}

// ---------- the check ----------

const CHECK_STEPS = [
  { key: "extract", label: "Finding the sender, dates, links and amounts", who: "Plainly's rules engine on AWS Lambda" },
  { key: "rules", label: "Checking the scam rules and the official contacts list", who: "Plain code, each rule with its source" },
];

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideFormError();
  if (letter?.status === "reading" || letter?.status === "preparing") {
    showFormError("Wait until your device has finished reading the letter, or press Cancel and paste the text.");
    return;
  }
  const text = textInput.value.trim();
  if (!text) {
    showFormError(letter
      ? "We have no words from this letter yet. Type or paste them in the box, then check."
      : "Add a photo or PDF of the letter, or paste its text, first.");
    (letter ? textInput : $("#file-input")).focus();
    return;
  }
  savePrefs();
  await runLiveCheck({ text, textSource, language: chosenLanguage(), level: chosenLevel(), deviceStep: deviceStep() });
});

// The receipt line for the reading done in this browser (the server's trace starts after it).
function deviceStep() {
  if (!letter || letter.status !== "done" || textSource === "typed") return null;
  if (letter.prepared.kind === "pdf_text") {
    return { step: "device", status: "done", detail: "Text taken from the PDF's own text layer (pdf.js), in your browser", ms: null };
  }
  const conf = letter.confidence != null ? `, average confidence ${Math.round(letter.confidence)}%` : "";
  return { step: "device", status: "done", ms: letter.ms,
    detail: `Tesseract read the ${letter.prepared.pages ? "PDF pages" : "photo"} in your browser (${letter.langs === "eng+hin" ? "English and Hindi" : "English"}${conf}); the file was not uploaded` };
}

async function runLiveCheck({ text, textSource: source, language, level, deviceStep: device = null }) {
  const view = ++viewSeq;
  submitBtn.disabled = true;
  const progress = renderProgress("Checking your letter", CHECK_STEPS);
  showInResults(progress.el);
  scrollToEl(resultsRegion);
  progress.set("extract");
  const timer = setTimeout(() => progress.set("rules"), 600);

  let check;
  try {
    check = await postJson("/check", { text, text_source: source, today: todayIso() });
  } catch (err) {
    if (view === viewSeq) showCheckError(err, () => runLiveCheck({ text, textSource: source, language, level, deviceStep: device }));
    return;
  } finally {
    clearTimeout(timer);
    submitBtn.disabled = false;
  }
  if (view !== viewSeq) return;

  const { letter_text: letterText = text, ...publicCheck } = check;
  current = { check: publicCheck, letterText, sample: null };
  showResult(publicCheck, null, device);
  await explainLive(language, level);
}

function showResult(check, sample, deviceStep = null) {
  explainSeq++;
  const explainSlot = h("section", { class: "block panel", id: "explanation", "aria-labelledby": "explain-title" },
    h("h2", { id: "explain-title" }, "In plain words"));
  showInResults(
    renderCheck(check, { sample, deviceStep }),
    explainSlot,
    h("p", null, h("button", { type: "button", class: "btn btn-quiet", onclick: startOver }, "Check another letter"))
  );
  announce(check.verdict_label || "Result ready");
  resultsRegion.focus({ preventScroll: true });
  scrollToEl(resultsRegion);
}

function explanationSlot() {
  const slot = $("#explanation");
  slot.replaceChildren(h("h2", { id: "explain-title" }, "In plain words"));
  return slot;
}

async function explainLive(language, level) {
  const seq = ++explainSeq;
  const shown = current;
  const stale = () => seq !== explainSeq || shown !== current;
  // Switching back to a language already shown costs no request (and no use of the hourly limit).
  const key = `${language}|${level}`;
  const cached = shown.explained?.get(key);
  if (cached) return showExplanation(cached, null, language);
  const slot = explanationSlot();
  const progress = renderProgress(`Getting the explanation in ${LANGUAGE_NAMES[language] || language}`,
    [{ key: "narrate", label: "Putting it in plain words", who: "Using only the checked facts above" }]);
  progress.set("narrate");
  slot.append(progress.el);
  try {
    const explain = await postJson("/explain", {
      letter_text: current.letterText, check: current.check, language, level, today: todayIso(),
    });
    if (stale()) return;
    const note = fallbackNote(explain, language, level);
    if (!note) (shown.explained ??= new Map()).set(key, explain);
    showExplanation(explain, note, language);
  } catch (err) {
    if (stale()) return;
    progress.el.remove();
    slot.append(h("div", { class: "notice notice-error" },
      h("h3", null, "The explanation couldn't be shown just now"),
      h("p", null, `${friendlyError(err).body} The check above still stands.`),
      h("button", { type: "button", class: "btn btn-small", onclick: () => explainLive(language, level) }, "Try the explanation again")));
  }
}

function showExplanation(explain, note, requestedLanguage) {
  const slot = explanationSlot();
  slot.append(renderExplanation(explain, current.check, { onCopy: copyReply, note }),
    renderLanguageSwitch(requestedLanguage || explain.language));
  announce("Explanation ready");
}

function showInResults(...nodes) {
  results.replaceChildren(...nodes);
  resultsRegion.hidden = nodes.length === 0;
}

function announce(message) {
  resultsStatus.textContent = "";
  // Set after a tick, so the same message twice in a row is still announced.
  setTimeout(() => { resultsStatus.textContent = message; }, 50);
}

// When the server could not give the explanation in the language asked for, it sends a short English one.
function fallbackNote(explain, language, level) {
  const sameLanguage = (explain.language || "").toLowerCase() === language.toLowerCase();
  if (!explain.meta?.fallback && !explain.meta?.fallback_language && sameLanguage) return null;
  const wanted = LANGUAGE_NAMES[language] || language;
  const text = language.toLowerCase() === "english"
    ? "We couldn't get the full explanation just now, so here is a short version. "
    : `We couldn't get this in ${wanted} just now, so here is a short version in English. `;
  return [text, h("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => explainLive(language, level) },
    "Try again")];
}

function renderLanguageSwitch(currentLanguage) {
  const select = h("select", { id: "relang" },
    Object.entries(LANGUAGE_NAMES).map(([value, name]) => h("option", { value }, name)));
  select.value = LANGUAGE_NAMES[currentLanguage] ? currentLanguage : "English";
  const go = () => {
    if (current.sample) showSampleExplanation(select.value);
    else explainLive(select.value, chosenLevel());
  };
  return h("div", { class: "explain-lang" },
    h("label", { for: "relang" }, "Explain it in another language"),
    h("div", null, select),
    h("button", { type: "button", class: "btn btn-quiet btn-small", onclick: go }, "Explain again"));
}

async function copyReply(area, status) {
  try {
    await navigator.clipboard.writeText(area.value);
  } catch {
    area.select();
    document.execCommand("copy");
  }
  status.textContent = "Copied. Paste it into your email or letter.";
}

function startOver() {
  viewSeq++;
  explainSeq++;
  current = null;
  showInResults();
  clearFile();
  textInput.value = "";
  textSource = "typed";
  syncTextLabel();
  scrollToEl(form);
  $("#file-input").focus({ preventScroll: true });
}

// ---------- errors ----------

function friendlyError(err) {
  const status = err instanceof ApiError ? err.status : -1;
  if (status === 400 || status === 413) {
    return { title: "We couldn't check that", body: err.message || "Check the text in the box matches your letter, then try again.", limit: false };
  }
  if (status === 429) {
    return { title: "You've checked a lot of letters this hour",
      body: "To keep Plainly free, each person can check a limited number of letters an hour. Please try again later. The sample letters below still open instantly.", limit: true };
  }
  if (status === 503) {
    return { title: "Plainly has reached today's limit",
      body: "We've used up today's free checks. Please come back tomorrow. The sample letters below still open instantly.", limit: true };
  }
  if (status === 0) {
    return { title: "We couldn't reach Plainly", body: "Check your internet connection and try again.", limit: false };
  }
  return { title: "Something went wrong while checking the letter",
    body: "Please try again in a minute. Your text is still in the box above.", limit: false };
}

function showCheckError(err, retry) {
  const f = friendlyError(err);
  const actions = h("div", { class: "btn-row" },
    f.limit ? null : h("button", { type: "button", class: "btn btn-small", onclick: retry }, "Try again"),
    h("button", { type: "button", class: f.limit ? "btn btn-small" : "btn btn-quiet btn-small",
      onclick: () => { scrollToEl($("#samples")); $("#samples .tile:not(:disabled)")?.focus({ preventScroll: true }); } },
      "Open a sample letter"));
  showInResults(h("div", { class: `notice ${f.limit ? "notice-limit" : "notice-error"}`, role: "alert" },
    h("h2", null, f.title), h("p", null, f.body), actions));
  scrollToEl(resultsRegion);
}

// ---------- samples ----------

async function openSample(tile) {
  const id = tile.dataset.sample;
  let data;
  try {
    data = await getSample(id);
  } catch (err) {
    showCheckError(err, () => openSample(tile));
    return;
  }
  const check = data.check && typeof data.check === "object" ? data.check : data;
  const { letter_text: _unused, explanations, explain, ...publicCheck } = check;
  viewSeq++;
  const sample = {
    id,
    title: tile.dataset.title,
    alt: tile.dataset.alt || null,
    image: tile.dataset.image || null,
    preview: tile.dataset.preview || null,
    mock: Boolean(data.mock),
    explanations: normalizeExplanations(data.explanations || explanations || data.explain || explain),
  };
  current = { check: publicCheck, letterText: "", sample };
  showResult(publicCheck, sample);
  showSampleExplanation(chosenLanguage());
  history.replaceState(null, "", `?sample=${encodeURIComponent(id)}`);
}

function normalizeExplanations(value) {
  if (!value || typeof value !== "object") return {};
  if (typeof value.tldr === "string") return { [value.language || "English"]: value };
  return value;
}

function showSampleExplanation(language) {
  explainSeq++;
  const all = current.sample.explanations;
  const key = Object.keys(all).find((k) => k.toLowerCase() === language.toLowerCase());
  if (key) return showExplanation(all[key], null, key);
  const fallback = all.English || Object.values(all)[0];
  if (!fallback) {
    explanationSlot().append(h("p", null, "This sample has no prepared explanation. Check a letter of your own to get one."));
    return;
  }
  const available = Object.keys(all).map((k) => LANGUAGE_NAMES[k] || k).join(" and ");
  showExplanation(fallback, `This sample was prepared in ${available} only.`, "English");
}

for (const tile of document.querySelectorAll(".tile[data-sample]")) {
  tile.addEventListener("click", () => openSample(tile));
}

// ---------- start ----------

loadPrefs();
syncTextLabel();

const deepLink = new URLSearchParams(location.search).get("sample");
if (deepLink) {
  const tile = [...document.querySelectorAll(".tile[data-sample]")].find((t) => t.dataset.sample === deepLink);
  if (tile && !tile.disabled) {
    openSample(tile);
  } else {
    showInResults(h("div", { class: "notice notice-limit" },
      h("h2", null, "That sample isn't ready yet"),
      h("p", null, "Its result is still being prepared. The other samples below open instantly.")));
  }
}
