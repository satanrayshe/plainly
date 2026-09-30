// /try/ page: collect a letter, call /api/check then /api/explain, render the results.

import { h, scrollToEl } from "./js/dom.js";
import { todayIso } from "./js/dates.js";
import { prepareFile, blobToBase64, UserFacingError } from "./js/prepare.js";
import { postJson, getSample, ApiError } from "./js/api.js";
import { renderCheck, renderProgress, renderExplanation } from "./js/render.js";

const $ = (sel) => document.querySelector(sel);
const form = $("#check-form");
const results = $("#results");
const textInput = $("#text-input");
const languageSelect = $("#language");
const otherWrap = $("#other-lang-wrap");
const otherInput = $("#other-lang");
const formError = $("#form-error");
const submitBtn = $("#submit-btn");
const chosen = $("#chosen");
const dropzone = $("#dropzone");

const PREFS_KEY = "plainly.prefs";
const LANGUAGE_NAMES = { English: "English", Hindi: "हिन्दी", Spanish: "Español" };

// The prepared image for the next submit: { promise, blob, previewUrl } or null.
let prepared = null;
// The last check shown, used by "explain in another language".
let current = null;

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
  if (LANGUAGE_NAMES[language]) {
    languageSelect.value = language;
  } else {
    languageSelect.value = "other";
    otherInput.value = language;
  }
  if (prefs.level === "normal") $("#level-normal").checked = true;
  syncOtherLanguage();
}

function savePrefs() {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify({ language: chosenLanguage() || "English", level: chosenLevel() }));
  } catch {
    // Storage can be unavailable; preferences are a convenience only.
  }
}

function chosenLanguage() {
  return languageSelect.value === "other" ? otherInput.value.trim().slice(0, 40) : languageSelect.value;
}

function chosenLevel() {
  return form.elements.level.value === "normal" ? "normal" : "simple";
}

function syncOtherLanguage() {
  otherWrap.hidden = languageSelect.value !== "other";
}

// ---------- choosing a file ----------

function setFile(file) {
  clearFile();
  hideFormError();
  const entry = { blob: null, previewUrl: null };
  entry.promise = prepareFile(file).then((out) => {
    entry.blob = out.blob;
    entry.previewUrl = URL.createObjectURL(out.blob);
    showChosen(file, out, entry.previewUrl);
    return out;
  });
  entry.promise.catch((err) => {
    if (prepared === entry) clearFile();
    showFormError(err instanceof UserFacingError ? err.message : "We couldn't open that file. Try a photo or a PDF.");
  });
  prepared = entry;
  chosen.hidden = false;
  chosen.replaceChildren(h("p", { class: "muted", role: "status" }, `Preparing ${file.name}…`));
}

function showChosen(file, out, previewUrl) {
  const kb = Math.round(out.blob.size / 1024);
  let detail = `Ready to send: ${kb} KB.`;
  if (out.pages) {
    detail = `PDF: we will read ${out.pages === 1 ? "page 1" : `pages 1 to ${out.pages}`}` +
      `${out.totalPages > out.pages ? ` of ${out.totalPages}` : ""}. ${detail}`;
  }
  chosen.replaceChildren(
    h("div", { class: "chosen" },
      h("img", { src: previewUrl, alt: "Preview of the letter you chose" }),
      h("div", null,
        h("p", null, h("strong", null, file.name)),
        h("p", { class: "muted small" }, detail),
        h("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => { clearFile(); $("#file-input").focus(); } }, "Remove")))
  );
}

function clearFile() {
  if (prepared?.previewUrl) URL.revokeObjectURL(prepared.previewUrl);
  prepared = null;
  chosen.hidden = true;
  chosen.replaceChildren();
  $("#file-input").value = "";
  $("#camera-input").value = "";
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

const CHECK_STEPS_IMAGE = [
  { key: "prep", label: "Preparing your photo", who: "On your device" },
  { key: "ocr", label: "Reading the letter", who: "Amazon Textract, an independent reader" },
  { key: "extract", label: "Finding the sender, dates and exact quotes", who: "Amazon Nova" },
  { key: "rules", label: "Checking rules and official contacts", who: "Plain code, no AI" },
];
const CHECK_STEPS_TEXT = [
  { key: "extract", label: "Finding the sender, dates and exact quotes", who: "Amazon Nova" },
  { key: "rules", label: "Checking rules and official contacts", who: "Plain code, no AI" },
];

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideFormError();
  const text = textInput.value.trim();
  const language = chosenLanguage();
  if (!prepared && !text) {
    showFormError("Add a photo or PDF of the letter, or paste its text, first.");
    return;
  }
  if (!language) {
    showFormError("Type the language you would like the explanation in.");
    otherInput.focus();
    return;
  }
  savePrefs();

  let image = null;
  if (prepared) {
    try {
      await prepared.promise;
    } catch {
      return; // the preparation error is already on screen
    }
    image = { type: "image/jpeg", data: await blobToBase64(prepared.blob) };
  }
  await runLiveCheck({ image, text, language, level: chosenLevel() });
});

async function runLiveCheck({ image, text, language, level }) {
  submitBtn.disabled = true;
  const steps = image ? CHECK_STEPS_IMAGE : CHECK_STEPS_TEXT;
  const progress = renderProgress("Checking your letter", steps);
  results.replaceChildren(progress.el);
  scrollToEl(results);

  // The check is one request; the steps advance on typical timings so the wait is legible.
  const timeline = image ? [["ocr", 0], ["extract", 2500], ["rules", 8000]] : [["extract", 0], ["rules", 5000]];
  const timers = timeline.map(([key, at]) => setTimeout(() => progress.set(key), at));

  let check;
  try {
    check = await postJson("/check", { image, text: text || null, today: todayIso() });
  } catch (err) {
    showCheckError(err, () => runLiveCheck({ image, text, language, level }));
    return;
  } finally {
    timers.forEach(clearTimeout);
    submitBtn.disabled = false;
  }

  const { letter_text: letterText = "", ...publicCheck } = check;
  current = { check: publicCheck, letterText, sample: null };
  showResult(publicCheck, null);
  await explainLive(language, level);
}

function showResult(check, sample) {
  const explainSlot = h("section", { class: "block panel", id: "explanation", "aria-labelledby": "explain-title" },
    h("h2", { id: "explain-title" }, "In plain words"));
  results.replaceChildren(
    renderCheck(check, { sample }),
    explainSlot,
    h("p", null, h("button", { type: "button", class: "btn btn-quiet", onclick: startOver }, "Check another letter"))
  );
  results.focus({ preventScroll: true });
  scrollToEl(results);
}

function explanationSlot() {
  const slot = $("#explanation");
  slot.replaceChildren(h("h2", { id: "explain-title" }, "In plain words"));
  return slot;
}

async function explainLive(language, level) {
  const slot = explanationSlot();
  const progress = renderProgress(`Writing the explanation in ${LANGUAGE_NAMES[language] || language}`,
    [{ key: "narrate", label: "Explaining in plain words", who: "Amazon Nova, using only the checked facts above" }]);
  progress.set("narrate");
  slot.append(progress.el);
  try {
    const explain = await postJson("/explain", {
      letter_text: current.letterText, check: current.check, language, level,
    });
    showExplanation(explain);
  } catch (err) {
    progress.el.remove();
    slot.append(h("div", { class: "notice notice-error" },
      h("h3", null, "The explanation couldn't be written just now"),
      h("p", null, `${friendlyError(err).body} The check above still stands.`),
      h("button", { type: "button", class: "btn btn-small", onclick: () => explainLive(language, level) }, "Try the explanation again")));
  }
}

function showExplanation(explain, note) {
  const slot = explanationSlot();
  slot.append(renderExplanation(explain, current.check, { onCopy: copyReply, note }), renderLanguageSwitch(explain.language));
}

function renderLanguageSwitch(currentLanguage) {
  const select = h("select", { id: "relang" },
    Object.entries(LANGUAGE_NAMES).map(([value, name]) => h("option", { value }, name)),
    h("option", { value: "other" }, "Another language…"));
  select.value = LANGUAGE_NAMES[currentLanguage] ? currentLanguage : "English";
  const other = h("input", { type: "text", maxlength: 40, placeholder: "Which language?", "aria-label": "Which language?", hidden: true });
  select.addEventListener("change", () => { other.hidden = select.value !== "other"; });
  const go = () => {
    const language = select.value === "other" ? other.value.trim() : select.value;
    if (!language) return other.focus();
    if (current.sample) showSampleExplanation(language);
    else explainLive(language, chosenLevel());
  };
  return h("div", { class: "explain-lang" },
    h("label", { for: "relang" }, "Explain it in another language"),
    h("div", null, select, other),
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
  current = null;
  results.replaceChildren();
  clearFile();
  textInput.value = "";
  scrollToEl(form);
  $("#file-input").focus({ preventScroll: true });
}

// ---------- errors ----------

function friendlyError(err) {
  const status = err instanceof ApiError ? err.status : -1;
  if (status === 400 || status === 413) {
    return { title: "We couldn't read that", body: err.message || "Try a clearer, closer photo of the letter, or paste its text instead.", limit: false };
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
  return { title: "Something went wrong while reading the letter",
    body: "Please try again in a minute. If it keeps happening, try a clearer photo or paste the text instead.", limit: false };
}

function showCheckError(err, retry) {
  const f = friendlyError(err);
  const actions = h("div", { class: "btn-row" },
    f.limit ? null : h("button", { type: "button", class: "btn btn-small", onclick: retry }, "Try again"),
    h("button", { type: "button", class: f.limit ? "btn btn-small" : "btn btn-quiet btn-small",
      onclick: () => { scrollToEl($("#samples")); $("#samples .tile:not(:disabled)")?.focus({ preventScroll: true }); } },
      "Open a sample letter"));
  results.replaceChildren(h("div", { class: `notice ${f.limit ? "notice-limit" : "notice-error"}`, role: "alert" },
    h("h2", null, f.title), h("p", null, f.body), actions));
  scrollToEl(results);
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
  const sample = {
    id,
    title: tile.dataset.title,
    alt: tile.dataset.alt || null,
    image: tile.dataset.image || null,
    mock: Boolean(data.mock),
    explanations: normalizeExplanations(data.explanations || explanations || data.explain || explain),
  };
  current = { check: publicCheck, letterText: "", sample };
  showResult(publicCheck, sample);
  showSampleExplanation(chosenLanguage() || "English");
  history.replaceState(null, "", `?sample=${encodeURIComponent(id)}`);
}

function normalizeExplanations(value) {
  if (!value || typeof value !== "object") return {};
  if (typeof value.tldr === "string") return { [value.language || "English"]: value };
  return value;
}

function showSampleExplanation(language) {
  const all = current.sample.explanations;
  const key = Object.keys(all).find((k) => k.toLowerCase() === language.toLowerCase());
  if (key) return showExplanation(all[key]);
  const fallback = all.English || Object.values(all)[0];
  if (!fallback) {
    explanationSlot().append(h("p", null, "This sample has no prepared explanation. Check a letter of your own to get one in any language."));
    return;
  }
  const available = Object.keys(all).map((k) => LANGUAGE_NAMES[k] || k).join(" and ");
  showExplanation(fallback,
    `This sample was prepared in ${available} only. For ${language}, check a letter of your own; the live checker writes in any language.`);
}

for (const tile of document.querySelectorAll(".tile[data-sample]")) {
  tile.addEventListener("click", () => openSample(tile));
}

// ---------- start ----------

languageSelect.addEventListener("change", () => {
  syncOtherLanguage();
  if (languageSelect.value === "other") otherInput.focus();
});
loadPrefs();

const deepLink = new URLSearchParams(location.search).get("sample");
if (deepLink) {
  const tile = [...document.querySelectorAll(".tile[data-sample]")].find((t) => t.dataset.sample === deepLink);
  if (tile && !tile.disabled) {
    openSample(tile);
  } else {
    results.replaceChildren(h("div", { class: "notice notice-limit" },
      h("h2", null, "That sample isn't ready yet"),
      h("p", null, "Its result is still being prepared. The other samples below open instantly.")));
  }
}
