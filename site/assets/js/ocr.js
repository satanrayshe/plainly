// Reads text from images on the visitor's own device with Tesseract.js, self-hosted under /vendor/tesseract/.
// Nothing here talks to Plainly's API: the photo stays in the browser and only the text leaves it, later,
// when the person presses "Check this letter".
//
// The library (about 0.2 MB), the engine (about 3.9 MB, one of two builds) and the language data (3.0 MB for
// English, 1.4 MB more for Hindi) load only when a photo or a scanned PDF is chosen. The browser caches the
// engine; Tesseract keeps the language data in IndexedDB, so a second letter starts at once.

const BASE = "/vendor/tesseract";
const OEM_LSTM_ONLY = 1;

export class OcrCancelled extends Error {
  constructor() {
    super("cancelled");
    this.name = "OcrCancelled";
  }
}

let libPromise = null;
let worker = null; // { api, langs } once created
let workerPromise = null;
let onLog = null; // progress callback of the job in flight
let cancelJob = null; // rejects the job in flight

function loadLibrary() {
  libPromise ??= new Promise((resolve, reject) => {
    if (window.Tesseract) return resolve(window.Tesseract);
    const script = document.createElement("script");
    script.src = `${BASE}/tesseract.min.js`;
    script.async = true;
    script.onload = () => (window.Tesseract ? resolve(window.Tesseract) : reject(new Error("Tesseract missing")));
    script.onerror = () => reject(new Error("Tesseract failed to load"));
    document.head.append(script);
  }).catch((err) => {
    libPromise = null;
    throw err;
  });
  return libPromise;
}

async function getWorker(langs) {
  if (worker && worker.langs === langs) return worker.api;
  if (worker) {
    await worker.api.reinitialize(langs, OEM_LSTM_ONLY);
    worker.langs = langs;
    return worker.api;
  }
  workerPromise ??= (async () => {
    const Tesseract = await loadLibrary();
    const api = await Tesseract.createWorker(langs, OEM_LSTM_ONLY, {
      workerPath: `${BASE}/worker.min.js`,
      corePath: `${BASE}/core`, // the worker picks tesseract-core-simd-lstm.wasm.js, or -lstm.wasm.js without SIMD
      langPath: `${BASE}/lang`,
      workerBlobURL: false,
      gzip: true,
      logger: (m) => onLog?.(m),
      errorHandler: () => {},
    });
    worker = { api, langs };
    return api;
  })().finally(() => {
    workerPromise = null;
  });
  const api = await workerPromise;
  if (worker.langs !== langs) return getWorker(langs);
  return api;
}

// Stops the job in flight. Tesseract can't abort a recognition, so the worker is thrown away and the next
// job starts a new one (from the browser cache, so quickly).
export function cancelOcr() {
  const reject = cancelJob;
  cancelJob = null;
  onLog = null;
  const old = worker;
  worker = null;
  old?.api.terminate().catch(() => {});
  reject?.(new OcrCancelled());
}

/**
 * Recognise text in one or more images (canvases or blobs), in order.
 * langs: "eng" or "eng+hin".
 * onProgress({ phase: "load" | "read", page, pages, fraction }) with fraction 0..1 over the whole job.
 * Resolves { text, confidence (0-100, mean over pages), ms }.
 */
export function recognize(images, langs, onProgress) {
  cancelOcr();
  const started = performance.now();
  const pages = images.length;
  let page = 0;
  // Loading takes the first 15% of the bar, reading the rest, split evenly across pages.
  const report = (phase, part) => {
    const fraction = phase === "load" ? 0.15 * part : 0.15 + 0.85 * ((page + part) / pages);
    onProgress?.({ phase, page: page + 1, pages, fraction: Math.min(1, fraction) });
  };
  let mine = null;
  const job = new Promise((resolve, reject) => {
    mine = reject;
    cancelJob = reject;
    onLog = (m) => {
      const p = typeof m.progress === "number" ? m.progress : 0;
      if (m.status === "recognizing text") report("read", p);
      else if (/loading|initializ/.test(m.status || "")) report("load", p);
    };
    (async () => {
      report("load", 0);
      const api = await getWorker(langs);
      const texts = [];
      let confidence = 0;
      for (page = 0; page < pages; page++) {
        report("read", 0);
        const { data } = await api.recognize(images[page]);
        texts.push(tidy(data.text || ""));
        confidence += data.confidence || 0;
      }
      return { text: texts.filter(Boolean).join("\n\n"), confidence: confidence / pages, ms: Math.round(performance.now() - started) };
    })().then(resolve, reject);
  });
  return job.finally(() => {
    if (cancelJob === mine) {
      cancelJob = null;
      onLog = null;
    }
  });
}

// Tesseract leaves stray spaces and runs of blank lines; the rules read words, so tidy both.
function tidy(text) {
  return text
    .replace(/[ \t]+\n/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
