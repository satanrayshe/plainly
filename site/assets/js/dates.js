// Dates arrive as plain YYYY-MM-DD strings (computed on the server, never by the model).
// Treat them as local calendar days so "days left" matches the reader's wall calendar.

export function parseDay(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isNaN(d.getTime()) ? null : d;
}

export function todayIso() {
  const d = new Date();
  return [d.getFullYear(), pad(d.getMonth() + 1), pad(d.getDate())].join("-");
}

export function pad(n) {
  return String(n).padStart(2, "0");
}

const longFormat = new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
const shortFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric" });

export function formatDay(iso, { weekday = true } = {}) {
  const d = parseDay(iso);
  if (!d) return iso || "";
  return (weekday ? longFormat : shortFormat).format(d);
}

export function daysFromToday(iso) {
  const d = parseDay(iso);
  if (!d) return null;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((d - today) / 86400000);
}

export function describeCountdown(days) {
  if (days == null) return "";
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "yesterday";
  return days > 0 ? `${days} days from today` : `${-days} days ago`;
}
