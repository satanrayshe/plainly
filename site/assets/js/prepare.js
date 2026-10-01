// Turns a chosen photo or PDF into something the on-device reader can use. Nothing leaves the browser here.
//   Photo      -> one grayscale canvas, long edge about 2000 px, for Tesseract (text_source "device_ocr")
//   PDF        -> the PDF's own text layer from pdf.js when it has real text (text_source "pdf_text"),
//                 otherwise its first 3 pages drawn as grayscale canvases for Tesseract ("device_ocr")

const MAX_EDGE = 2000;
const MIN_EDGE = 1400; // small screenshots are enlarged: Tesseract reads best with letters 20-30 px tall
const PREVIEW_EDGE = 480;
const PDF_MAX_PAGES = 3;
const PDF_OCR_WIDTH = 1700; // about 200 dpi on a letter-size page
const PDF_MIN_TEXT = 80; // fewer real characters than this means a scanned PDF
const PDFJS = "/vendor/pdfjs/pdf.min.js";

export class UserFacingError extends Error {}

export function isPdf(file) {
  return file.type === "application/pdf" || /\.pdf$/i.test(file.name);
}

export async function prepareFile(file) {
  if (isPdf(file)) return preparePdf(file);
  if (file.type.startsWith("image/") || /\.(jpe?g|png|webp|gif|bmp|heic|heif)$/i.test(file.name)) return prepareImage(file);
  throw new UserFacingError("That file type isn't supported. Please choose a photo (JPG or PNG) or a PDF.");
}

async function prepareImage(file) {
  const source = await decodeImage(file);
  const { width, height } = source;
  const long = Math.max(width, height);
  const scale = long > MAX_EDGE ? MAX_EDGE / long : long < MIN_EDGE ? Math.min(2, MIN_EDGE / long) : 1;
  const canvas = drawOnWhite(source, Math.round(width * scale), Math.round(height * scale));
  source.close?.();
  const preview = await previewUrl(canvas);
  toGrayscale(canvas);
  return { kind: "image", images: [canvas], preview, pages: null };
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
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, width, height);
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(source, 0, 0, width, height);
  return canvas;
}

// Grayscale, then stretch the levels so the darkest 1% is black and the lightest 1% white. Phone photos of
// paper are often grey-on-grey; Tesseract's own thresholding does better on the stretched image.
function toGrayscale(canvas) {
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const px = img.data;
  const hist = new Uint32Array(256);
  for (let i = 0; i < px.length; i += 4) {
    const y = (px[i] * 77 + px[i + 1] * 150 + px[i + 2] * 29) >> 8;
    px[i] = y;
    hist[y]++;
  }
  const total = px.length / 4;
  let lo = 0;
  let hi = 255;
  for (let seen = 0; lo < 255 && (seen += hist[lo]) < total * 0.01; lo++);
  for (let seen = 0; hi > 0 && (seen += hist[hi]) < total * 0.01; hi--);
  const range = hi - lo;
  const stretch = range > 40 && range < 250; // leave clean scans and near-blank images alone
  for (let i = 0; i < px.length; i += 4) {
    let y = px[i];
    if (stretch) y = Math.max(0, Math.min(255, Math.round(((y - lo) * 255) / range)));
    px[i] = px[i + 1] = px[i + 2] = y;
  }
  ctx.putImageData(img, 0, 0);
}

async function previewUrl(canvas) {
  const scale = Math.min(1, PREVIEW_EDGE / Math.max(canvas.width, canvas.height));
  const small = scale < 1 ? drawOnWhite(canvas, Math.round(canvas.width * scale), Math.round(canvas.height * scale)) : canvas;
  const blob = await new Promise((resolve) => small.toBlob(resolve, "image/jpeg", 0.8));
  return blob ? URL.createObjectURL(blob) : null;
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
    throw new UserFacingError("We couldn't load the PDF reader. Check your connection, or paste the letter's text instead.");
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

  try {
    const totalPages = doc.numPages;
    const count = Math.min(PDF_MAX_PAGES, totalPages);
    const pages = [];
    for (let n = 1; n <= count; n++) pages.push(await doc.getPage(n));

    const first = await renderPage(pages[0], PREVIEW_EDGE);
    const preview = await previewUrl(first);

    // A PDF made by a computer carries its text: use it as is, no reading needed.
    const text = (await Promise.all(pages.map(pageText))).filter(Boolean).join("\n\n").trim();
    if (text.replace(/\s/g, "").length >= PDF_MIN_TEXT) {
      return { kind: "pdf_text", text, preview, pages: count, totalPages };
    }

    // A scanned PDF is pictures of pages: draw them and read them like photos.
    const images = [];
    for (const page of pages) {
      const canvas = await renderPage(page, PDF_OCR_WIDTH);
      toGrayscale(canvas);
      images.push(canvas);
    }
    return { kind: "pdf_scan", images, preview, pages: count, totalPages };
  } finally {
    doc.destroy();
  }
}

async function renderPage(page, width) {
  const scale = width / page.getViewport({ scale: 1 }).width;
  const viewport = page.getViewport({ scale });
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(viewport.width);
  canvas.height = Math.round(viewport.height);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  await page.render({ canvasContext: ctx, viewport }).promise;
  return canvas;
}

// pdf.js gives text in runs, with its own space runs between words; hasEOL marks the end of a line.
async function pageText(page) {
  const content = await page.getTextContent();
  let out = "";
  for (const item of content.items) {
    if (typeof item.str !== "string") continue;
    out += item.str;
    if (item.hasEOL) out += "\n";
  }
  return out.replace(/[ \t]+\n/g, "\n").replace(/[ \t]{2,}/g, " ").replace(/\n{3,}/g, "\n\n").trim();
}
