// Turns a chosen photo or PDF into one JPEG small enough to send (<= 1.5 MB).
// Photos: long edge capped at 2000 px. PDFs: first 3 pages rendered with pdf.js and stacked.

const MAX_BYTES = 1.5 * 1024 * 1024;
const MAX_EDGE = 2000;
const PDF_MAX_PAGES = 3;
const PDF_PAGE_WIDTH = 1100; // about 130 dpi on a letter-size page: enough for OCR, small enough to send
const QUALITIES = [0.86, 0.76, 0.66, 0.56];
const PDFJS = "/vendor/pdfjs/pdf.min.js";

export class UserFacingError extends Error {}

export async function prepareFile(file) {
  const isPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name);
  if (isPdf) return preparePdf(file);
  if (file.type.startsWith("image/") || /\.(jpe?g|png|webp|gif|heic|heif)$/i.test(file.name)) return prepareImage(file);
  throw new UserFacingError("That file type isn't supported. Please choose a photo (JPG or PNG) or a PDF.");
}

async function prepareImage(file) {
  const source = await decodeImage(file);
  const { width, height } = source;
  const scale = Math.min(1, MAX_EDGE / Math.max(width, height));
  const canvas = drawOnWhite(source, Math.round(width * scale), Math.round(height * scale));
  source.close?.();
  const blob = await encodeWithinLimit(canvas);
  return { blob, width: canvas.width, height: canvas.height, pages: null };
}

async function decodeImage(file) {
  if ("createImageBitmap" in window) {
    try {
      return await createImageBitmap(file, { imageOrientation: "from-image" });
    } catch {
      // Fall through to <img>, which handles a few formats createImageBitmap refuses.
    }
  }
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.decoding = "async";
    img.src = url;
    await img.decode();
    return img;
  } catch {
    throw new UserFacingError(
      "We couldn't open this photo. If it's an iPhone HEIC photo, take a screenshot of it and upload that instead."
    );
  } finally {
    URL.revokeObjectURL(url);
  }
}

function drawOnWhite(source, width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, width, height);
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(source, 0, 0, width, height);
  return canvas;
}

function toJpeg(canvas, quality) {
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("encode failed"))), "image/jpeg", quality)
  );
}

async function encodeWithinLimit(canvas) {
  let current = canvas;
  for (let shrink = 0; shrink < 4; shrink++) {
    for (const q of QUALITIES) {
      const blob = await toJpeg(current, q);
      if (blob.size <= MAX_BYTES) return blob;
    }
    current = drawOnWhite(current, Math.round(current.width * 0.8), Math.round(current.height * 0.8));
  }
  throw new UserFacingError("This picture is too large to send. Try a photo of just the letter, closer up.");
}

let pdfjsPromise;
function loadPdfJs() {
  pdfjsPromise ??= import(PDFJS).then((lib) => {
    lib.GlobalWorkerOptions.workerSrc = "/vendor/pdfjs/pdf.worker.min.js";
    return lib;
  });
  return pdfjsPromise;
}

async function preparePdf(file) {
  let pdfjs;
  try {
    pdfjs = await loadPdfJs();
  } catch {
    pdfjsPromise = undefined;
    throw new UserFacingError("We couldn't load the PDF reader. Check your connection, or upload a photo instead.");
  }
  let doc;
  try {
    doc = await pdfjs.getDocument({
      data: new Uint8Array(await file.arrayBuffer()),
      standardFontDataUrl: "/vendor/pdfjs/standard_fonts/",
      isEvalSupported: false,
    }).promise;
  } catch (err) {
    if (err?.name === "PasswordException") {
      throw new UserFacingError("This PDF is password-protected. Open it, take a screenshot, and upload that instead.");
    }
    throw new UserFacingError("We couldn't open this PDF. Try a photo or a screenshot of the letter instead.");
  }

  const totalPages = doc.numPages;
  const count = Math.min(PDF_MAX_PAGES, totalPages);
  const pages = [];
  for (let n = 1; n <= count; n++) {
    const page = await doc.getPage(n);
    const scale = PDF_PAGE_WIDTH / page.getViewport({ scale: 1 }).width;
    const viewport = page.getViewport({ scale });
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(viewport.width);
    canvas.height = Math.round(viewport.height);
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    await page.render({ canvasContext: ctx, viewport }).promise;
    pages.push(canvas);
  }
  doc.destroy();

  const gap = 16;
  const width = Math.max(...pages.map((c) => c.width));
  const height = pages.reduce((sum, c) => sum + c.height, 0) + gap * (pages.length - 1);
  const stacked = document.createElement("canvas");
  stacked.width = width;
  stacked.height = height;
  const ctx = stacked.getContext("2d");
  ctx.fillStyle = "#c8c8c8"; // the gap reads as a page break
  ctx.fillRect(0, 0, width, height);
  let y = 0;
  for (const c of pages) {
    ctx.drawImage(c, 0, y);
    y += c.height + gap;
  }
  const blob = await encodeWithinLimit(stacked);
  return { blob, width: stacked.width, height: stacked.height, pages: count, totalPages };
}

export function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}
