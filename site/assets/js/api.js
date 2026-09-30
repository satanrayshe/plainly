// Same-origin JSON API. The base path comes from <meta name="plainly-api"> so it can be
// changed at deploy time without touching code (never from the URL, which a link could forge).

const BASE = (document.querySelector('meta[name="plainly-api"]')?.content || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(status, message) {
    super(message || `HTTP ${status}`);
    this.status = status; // 0 = network failure or timeout
  }
}

export async function postJson(path, body, { timeoutMs = 45000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, "");
  } finally {
    clearTimeout(timer);
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    // Non-JSON error pages (e.g. a gateway timeout) fall through with data = null.
  }
  if (!res.ok) throw new ApiError(res.status, data?.error || "");
  if (!data) throw new ApiError(502, "");
  return data;
}

export async function getSample(id) {
  const res = await fetch(`/samples/results/${encodeURIComponent(id)}.json`, { cache: "no-cache" });
  if (!res.ok) throw new ApiError(res.status, "");
  return res.json();
}
