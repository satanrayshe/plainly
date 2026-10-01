// Reads text from images on the visitor's own device with Tesseract.js, self-hosted under /vendor/tesseract/.
// Nothing here talks to Plainly's API: the photo stays in the browser and only the text leaves it, later,
// when the person presses "Check this letter".
//
// The library (about 0.2 MB), the engine (about 3.9 MB, one of two builds) and the language data (3.0 MB for
// English, 1.4 MB more for Hindi) load only when a photo or a scanned PDF is chosen. The browser caches the
// engine; Tesseract keeps the language data in IndexedDB. The worker is kept between letters, so a second letter
// in the same visit starts at once; it is thrown away only when a reading is cancelled.

const BASE = "/vendor/tesseract";
const OEM_LSTM_ONLY = 1;

export class OcrCancelled extends Error {
  constructor() {
    super("cancelled");
    this.name = "OcrCancelled";
  }
}

let libPromise = null;
let worker = null; // { api, langs }: a ready worker, kept for the next letter
let pending = null; // { promise, langs, doomed }: a worker being created
let job = null; // the job in flight: { cancelled, reject, onLog }

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

// Starts creating a worker. If the job that asked for it is cancelled first, the entry is marked doomed: the
// worker is terminated as soon as it exists, is never reused, and its progress events go nowhere.
function createWorker(langs) {
  const entry = { langs, doomed: false, promise: null };
  entry.promise = (async () => {
    const Tesseract = await loadLibrary();
    const api = await Tesseract.createWorker(langs, OEM_LSTM_ONLY, {
      workerPath: `${BASE}/worker.min.js`,
      corePath: `${BASE}/core`, // the worker picks tesseract-core-simd-lstm.wasm.js, or -lstm.wasm.js without SIMD
      langPath: `${BASE}/lang`,
      workerBlobURL: false,
      gzip: true,
      logger: (m) => {
        if (!entry.doomed) job?.onLog?.(m);
      },
      errorHandler: () => {},
    });
    if (entry.doomed) {
      api.terminate().catch(() => {});
      throw new OcrCancelled();
    }
    worker = { api, langs };
    return api;
  })().finally(() => {
    if (pending === entry) pending = null;
  });
  return entry;
}

async function getWorker(langs) {
  if (worker && worker.langs === langs) return worker.api;
  if (worker) {
    await worker.api.reinitialize(langs, OEM_LSTM_ONLY);
    worker.langs = langs;
    return worker.api;
  }
  if (pending && pending.langs !== langs) {
    pending.doomed = true;
    pending = null;
  }
  pending ??= createWorker(langs);
  return pending.promise;
}

// Stops the job in flight, if there is one. Tesseract can't abort a recognition, so that job's worker is thrown
// away (or, while it is still being created, terminated as soon as it exists) and the next job starts a new one
// from the browser cache. With no job in flight the ready worker is kept.
export function cancelOcr() {
  const current = job;
  if (!current) return;
  job = null;
  current.cancelled = true;
  current.onLog = null;
  if (pending) {
    pending.doomed = true;
    pending = null;
  }
  const old = worker;
  worker = null;
  old?.api.terminate().catch(() => {});
  current.reject(new OcrCancelled());
}

// Tesseract reports each loading stage with its own 0..1 progress. Each stage gets its own slice of the first
// 15% of the bar, and the bar never moves backwards.
const LOAD_STAGES = [
  [/core/, 0, 0.06],
  [/language|traineddata/, 0.07, 0.13],
  [/api/, 0.13, 0.15],
  [/tesseract/, 0.06, 0.07],
];

/**
 * Recognise text in one or more images (canvases or blobs), in order.
 * langs: "eng" or "eng+hin".
 * onProgress({ phase: "load" | "read", page, pages, fraction }) with fraction 0..1 over the whole job, never
 * decreasing.
 * Resolves { text, confidence (0-100, mean over pages), ms }; rejects with OcrCancelled after cancelOcr().
 */
export function recognize(images, langs, onProgress) {
  cancelOcr(); // only one job at a time; a no-op when nothing is in flight, so the ready worker is reused
  const started = performance.now();
  const pages = images.length;
  let page = 0;
  let last = 0;
  const report = (phase, fraction) => {
    last = Math.max(last, Math.min(1, fraction));
    onProgress?.({ phase, page: page + 1, pages, fraction: last });
  };
  const me = { cancelled: false, reject: null, onLog: null };
  job = me;
  const stop = () => {
    if (me.cancelled) throw new OcrCancelled();
  };
  const promise = new Promise((resolve, reject) => {
    me.reject = reject;
    me.onLog = (m) => {
      const p = typeof m.progress === "number" ? m.progress : 0;
      const status = m.status || "";
      if (status === "recognizing text") {
        report("read", 0.15 + 0.85 * ((page + p) / pages));
      } else if (/loading|initializ/.test(status)) {
        const stage = LOAD_STAGES.find(([re]) => re.test(status));
        if (stage) report("load", stage[1] + (stage[2] - stage[1]) * p);
      }
    };
    (async () => {
      report("load", 0);
      const api = await getWorker(langs);
      stop();
      const texts = [];
      let confidence = 0;
      for (page = 0; page < pages; page++) {
        stop();
        report("read", 0.15 + 0.85 * (page / pages));
        const { data } = await api.recognize(images[page]);
        stop();
        texts.push(tidy(data.text || ""));
        confidence += data.confidence || 0;
      }
      return { text: texts.filter(Boolean).join("\n\n"), confidence: confidence / pages, ms: Math.round(performance.now() - started) };
    })().then(resolve, reject);
  });
  return promise.finally(() => {
    if (job === me) job = null;
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
