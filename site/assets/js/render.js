// Renders /api/check and /api/explain responses. Pure DOM building, no fetching.

import { h, icon } from "./dom.js";
import { formatDay, daysFromToday, describeCountdown, parseDay } from "./dates.js";
import { buildIcs, downloadIcs } from "./ics.js";

export const REDACTED_TEXT = "[instruction aimed at AI tools — hidden for safety, visible in the image]";

const VERDICTS = {
  likely_scam: { cls: "stamp-scam", icon: "scam", label: "Likely scam" },
  consistent_with_genuine: {
    cls: "stamp-ok",
    icon: "ok",
    label: "Consistent with a genuine letter. Confirm on the official number.",
  },
  cant_tell: { cls: "stamp-unsure", icon: "unsure", label: "Can't tell" },
};

const SEVERITY = {
  strong: { label: "Strong sign", order: 0 },
  medium: { label: "Warning sign", order: 1 },
  info: { label: "Note", order: 2 },
};

const STEP_NAMES = {
  ocr: "Independent reading (Amazon Textract)",
  extract: "Sender, dates and quotes (Amazon Nova)",
  registry: "Official contacts list",
  contacts: "Phone numbers, links and emails in the text",
  dates: "Deadline arithmetic",
  grounding: "Quotes checked against the reading",
  verdict: "Verdict",
  "rule:payment_method": "Payment method",
  "rule:payment_gift_card": "Payment by gift card",
  "rule:payment_crypto_wire": "Payment by crypto or wire transfer",
  "rule:payment_personal_upi": "Payment to a personal UPI ID",
  "rule:credential_request": "Asks for OTP, PIN or password",
  "rule:threat_arrest": "Threat of arrest",
  "rule:video_call": "Demands a video call",
  "rule:video_call_demand": "Demands a video call",
  "rule:ai_instruction": "Hidden instructions for AI tools",
  "rule:lookalike_domain": "Look-alike web address",
  "rule:urgency": "Very short deadline",
  "rule:urgency_short": "Very short deadline",
  "rule:freemail": "Free email as an official contact",
  "rule:freemail_official": "Free email as an official contact",
  "rule:secrecy": "Asks you to keep it secret",
  "rule:unknown_contact": "Contact not on the official list",
  "rule:injection_detected_model": "AI-aimed text noticed by the model",
};

const CHIP = {
  flag: "FLAG", pass: "PASS", unknown: "UNKNOWN", done: "DONE", skipped: "SKIPPED", failed: "FAILED",
};

const FALLBACK_REPORT = [
  { name: "India: National Cyber Crime Reporting Portal, helpline 1930", url: "https://cybercrime.gov.in" },
  { name: "United States: FTC", url: "https://reportfraud.ftc.gov" },
  { name: "United Kingdom: Report Fraud (formerly Action Fraud), 0300 123 2040", url: "https://www.reportfraud.police.uk" },
];

const LANG_CODES = { english: "en", hindi: "hi", spanish: "es" };

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url || "";
  }
}

function safeHref(url) {
  try {
    const u = new URL(url);
    return u.protocol === "https:" || u.protocol === "http:" ? u.href : null;
  } catch {
    return null;
  }
}

function stepName(step) {
  if (STEP_NAMES[step]) return STEP_NAMES[step];
  const bare = String(step).replace(/^rule:/, "").replace(/_/g, " ");
  return bare.charAt(0).toUpperCase() + bare.slice(1);
}

// ---------- verdict and flags ----------

export function renderStamp(check) {
  const v = VERDICTS[check.verdict] || VERDICTS.cant_tell;
  return h("p", { class: `stamp ${v.cls}` }, icon(v.icon), h("span", null, check.verdict_label || v.label));
}

function renderFlag(flag) {
  const sev = SEVERITY[flag.severity] ? flag.severity : "info";
  let quote = null;
  if (flag.quote_redacted) {
    quote = h("blockquote", { class: "quote redacted" }, REDACTED_TEXT);
  } else if (flag.quote) {
    quote = h("blockquote", { class: "quote" }, h("span", { class: "quote-label" }, "From the letter"), `“${flag.quote}”`);
  }
  let grounding = null;
  if (flag.grounded === true) {
    grounding = h("p", { class: "grounding" }, "Found word for word in the independent reading of the letter.");
  } else if (flag.grounded === false) {
    grounding = h("p", { class: "grounding no" },
      "Could not be matched to the independent reading, so it counts as a weaker sign.");
  }
  const source = safeHref(flag.source?.url)
    ? h("p", { class: "grounding" }, "Source: ", h("a", { href: flag.source.url, rel: "noopener" }, flag.source.name || hostOf(flag.source.url)))
    : null;
  return h("li", { class: `sev-block-${sev}` },
    h("p", { class: "flag-title" }, h("span", { class: `sev sev-${sev}` }, SEVERITY[sev].label), h("span", null, flag.title || stepName(flag.rule))),
    quote,
    flag.why ? h("p", { class: "why" }, flag.why) : null,
    grounding,
    source
  );
}

function renderFlags(check) {
  const flags = [...(check.flags || [])].sort(
    (a, b) => (SEVERITY[a.severity]?.order ?? 3) - (SEVERITY[b.severity]?.order ?? 3)
  );
  const ruleCount = (check.trace || []).filter((t) => String(t.step).startsWith("rule:")).length;
  const body = flags.length
    ? h("ul", { class: "flags" }, flags.map(renderFlag))
    : h("p", null,
        `No warning signs found${ruleCount ? ` in ${ruleCount} rule checks` : ""}. `,
        "That alone does not prove a letter is genuine, so still use the official number above.");
  return h("section", { class: "block panel", "aria-labelledby": "flags-title" },
    h("h2", { id: "flags-title" }, "What we found"), body);
}

// ---------- official number ----------

export function renderOfficial(check) {
  const agency = check.agency || null;
  const box = h("div", { class: "official" });
  const phone = agency?.official_phone;
  const site = safeHref(agency?.official_site);
  if (agency && (phone || site)) {
    const title = {
      likely_scam: "Do not call the number on this letter.",
      consistent_with_genuine: "Confirm it on the official number before you act.",
    }[check.verdict] || "Check with the organisation directly, not with the number in the letter.";
    box.append(h("h3", null, title));
    if (phone) {
      box.append(h("p", null, `Official ${agency.name} line:`, h("br"),
        h("a", { class: "phone", href: `tel:${phone.replace(/[^\d+]/g, "")}` }, phone)));
    } else {
      box.append(h("p", null, `Official ${agency.name} website: `, h("a", { href: site, rel: "noopener" }, hostOf(site))));
    }
    if (safeHref(agency.source_url)) {
      box.append(h("p", { class: "source" }, "Source: ",
        h("a", { href: agency.source_url, rel: "noopener" }, hostOf(agency.source_url)),
        agency.checked_on ? `, checked ${formatDay(agency.checked_on, { weekday: false })}` : ""));
    }
  } else {
    box.append(
      h("h3", null, "We could not match the sender to an official contact."),
      h("p", null, "Find the organisation's number yourself, on its official website or on a bill you already trust. Do not use the number in this letter.")
    );
  }
  if (check.verdict === "likely_scam") box.append(renderReport(check));
  return box;
}

// The agency's channel when one matched; otherwise the check's own report_channel (chosen by country).
function renderReport(check) {
  const channel = check.agency?.report_channel || check.report_channel;
  if (channel && safeHref(channel.url)) {
    return h("p", { class: "report" }, "Report it: ", h("a", { href: channel.url, rel: "noopener" }, channel.name || hostOf(channel.url)));
  }
  return h("div", { class: "report" }, h("p", null, "Report it:"),
    h("ul", { class: "plain-list" }, FALLBACK_REPORT.map((c) => h("li", null, h("a", { href: c.url, rel: "noopener" }, c.name)))));
}

// ---------- deadlines ----------

function renderDeadlines(check) {
  const deadlines = (check.extracted?.deadlines || []).filter((d) => parseDay(d.date));
  if (!deadlines.length) return null;
  const scam = check.verdict === "likely_scam";
  const items = deadlines.map((d) => {
    const countdown = describeCountdown(daysFromToday(d.date));
    const li = h("li", null,
      h("p", { class: "when" }, formatDay(d.date), countdown ? h("span", { class: "count" }, ` (${countdown})`) : null),
      d.what ? h("p", { class: "what" }, d.what) : null,
      d.computed_from ? h("p", { class: "computed" }, `Worked out in code: ${d.computed_from.replace(/_/g, " ")}.`) : null,
      d.quote ? h("blockquote", { class: "quote" }, h("span", { class: "quote-label" }, "From the letter"), `“${d.quote}”`) : null
    );
    if (scam) {
      li.append(h("p", { class: "why" }, "This deadline is part of the pressure. Do not act on it."));
    } else {
      li.append(h("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => saveDeadline(d, check) }, "Add to calendar"));
    }
    return li;
  });
  return h("section", { class: "block panel", "aria-labelledby": "deadlines-title" },
    h("h2", { id: "deadlines-title" }, scam ? "The deadline in this letter" : deadlines.length > 1 ? "Deadlines" : "Deadline"),
    h("ul", { class: `deadlines${scam ? " is-scam" : ""}` }, items));
}

function saveDeadline(deadline, check) {
  const agency = check.agency;
  const who = agency?.name || check.extracted?.claimed_sender || "letter";
  const lines = [];
  if (deadline.quote) lines.push(`From the letter: "${deadline.quote}"`);
  if (agency?.official_phone) lines.push(`Confirm on the official ${agency.name} number: ${agency.official_phone}`);
  lines.push("Added by Plainly. Not legal advice.");
  const text = buildIcs({
    date: deadline.date,
    summary: `${deadline.what || "Deadline"} (${who})`,
    description: lines.join("\n"),
  });
  downloadIcs(`plainly-deadline-${deadline.date}.ics`, text);
}

// ---------- receipts ----------

function renderReceipts(check) {
  const trace = check.trace || [];
  const flagged = trace.filter((t) => t.status === "flag").length;
  const seconds = check.meta?.ms ? `${(check.meta.ms / 1000).toFixed(1)} s` : null;
  const note = [`${trace.length} steps`, `${flagged} flagged`, seconds].filter(Boolean).join(" · ");

  const g = check.grounding;
  let groundingLine = null;
  if (g?.source === "textract") {
    groundingLine = `Quotes found in the independent reading (Amazon Textract): ${g.grounded} of ${g.total}.`;
  } else if (g?.source === "pasted_text") {
    groundingLine = `Quotes checked against the text you pasted: ${g.grounded} of ${g.total}.`;
  } else if (g?.source === "none") {
    groundingLine = "Quotes could not be checked against an independent reading, so strong signs count for less.";
  }
  const meta = check.meta || {};
  const tokens = meta.input_tokens > 0 ? `, ${meta.input_tokens} tokens in, ${meta.output_tokens} out` : "";

  return h("details", { class: "receipts" },
    h("summary", null, h("span", null, h("span", { class: "sum-title" }, "Receipts: every check we ran"), h("span", { class: "sum-note" }, note))),
    h("div", { class: "receipts-body" },
      h("p", null, "Each line is one step, in order. The rules are plain code; the AI model only reads the letter and explains it."),
      h("ol", { class: "trace" }, trace.map((t) =>
        h("li", null,
          h("span", null, h("span", { class: `chip chip-${t.status}` }, CHIP[t.status] || String(t.status || "").toUpperCase())),
          h("span", { class: "step" }, stepName(t.step), h("code", null, t.step)),
          h("span", { class: "ms" }, typeof t.ms === "number" ? `${t.ms} ms` : ""),
          t.detail ? h("span", { class: "detail" }, t.detail) : null
        ))),
      groundingLine ? h("p", { class: "mt" }, groundingLine) : null,
      meta.model ? h("p", { class: "small muted" }, `Model: ${meta.model}${tokens}.`) : null
    ));
}

// ---------- whole check ----------

export function renderCheck(check, { sample = null } = {}) {
  const sheet = h("article", { class: "result-sheet", "aria-labelledby": "verdict-title" });
  if (sample) {
    sheet.append(h("p", { class: "sample-banner" },
      h("strong", null, `Sample letter: ${sample.title}. `),
      "This result was prepared in advance, so nothing was uploaded."));
    if (sample.mock) sheet.append(h("p", { class: "mock-note" }, "Illustrative result, not from the live checker. It will be replaced by live output before launch."));
  }
  const top = h("div", { class: "result-top" },
    h("h2", { id: "verdict-title", class: "visually-hidden" }, "Verdict"),
    renderStamp(check),
    h("div", { class: "result-lead" },
      h("div", null,
        check.headline ? h("p", { class: "result-headline" }, check.headline) : null,
        check.extracted?.claimed_sender ? h("p", { class: "result-meta" }, `Says it is from: ${check.extracted.claimed_sender}`) : null),
      sample?.image ? h("a", { class: "letter-thumb", href: sample.image, title: "Open the sample letter" },
        h("img", { src: sample.image, alt: sample.alt || `The sample letter: ${sample.title}`, width: 96 })) : null)
  );
  sheet.append(top, renderOfficial(check), renderFlags(check));
  const deadlines = renderDeadlines(check);
  if (deadlines) sheet.append(deadlines);
  sheet.append(renderReceipts(check));
  return sheet;
}

// ---------- progress ----------

export function renderProgress(title, steps) {
  const list = h("ol", { class: "progress" }, steps.map((s) =>
    h("li", { "data-key": s.key }, h("span", { class: "mark", "aria-hidden": "true" }),
      h("span", null, s.label, h("span", { class: "who" }, s.who)))));
  const panel = h("div", { class: "panel", role: "status" }, h("h2", { class: "progress-title" }, title), list);
  return {
    el: panel,
    set(key) {
      let reached = false;
      for (const li of list.children) {
        const isCurrent = li.dataset.key === key;
        li.classList.toggle("active", isCurrent);
        li.classList.toggle("done", !reached && !isCurrent);
        if (isCurrent) reached = true;
      }
    },
  };
}

// ---------- explanation ----------

function langAttrs(language) {
  const code = LANG_CODES[String(language || "").toLowerCase()];
  return code ? { lang: code, dir: "auto" } : { dir: "auto" };
}

export function renderExplanation(explain, check, { onCopy, note } = {}) {
  const la = langAttrs(explain.language);
  const scam = check.verdict === "likely_scam";
  const block = h("div", { class: "explain-body" });
  if (note) block.append(h("p", { class: "sample-banner" }, note));
  if (explain.tldr) block.append(h("p", { class: "tldr", ...la }, explain.tldr));

  const section = (title, content) => (content ? [h("h3", null, title), content] : []);
  const points = explain.explanation?.length ? h("ul", { class: "points", ...la }, explain.explanation.map((p) => h("li", null, p))) : null;
  const actions = explain.actions?.length
    ? h("ol", { class: "actions", ...la }, explain.actions.map((a) => h("li", null,
        h("p", { class: "step" }, a.step),
        a.how ? h("p", { class: "how" }, a.how) : null,
        parseDay(a.by) ? h("p", { class: "by" }, `By ${formatDay(a.by)}`) : null)))
    : null;
  const jargon = explain.jargon?.length
    ? h("dl", { class: "jargon", ...la }, explain.jargon.flatMap((j) => [h("dt", null, j.term), h("dd", null, j.meaning)]))
    : null;
  const questions = explain.questions_to_ask?.length
    ? h("ul", { class: "points", ...la }, explain.questions_to_ask.map((q) => h("li", null, q)))
    : null;

  block.append(
    ...section("What it says", points),
    ...section(scam ? "What to do now" : "What to do", actions),
    ...section("Words you may not know", jargon),
    ...section(scam ? "If you want to check" : "Questions to ask", questions)
  );

  if (scam || !explain.reply_draft) {
    if (scam) {
      block.append(h("div", { class: "notice notice-error mt" },
        h("h3", null, "Don't reply to this message"),
        h("p", null, "Replying tells the sender your number or address is active. Report it instead."),
        renderReport(check)));
    }
  } else {
    const area = h("textarea", { id: "reply-draft", "aria-describedby": "reply-hint" });
    area.value = explain.reply_draft;
    const status = h("p", { class: "status-line", role: "status" });
    block.append(h("div", { class: "reply" },
      h("h3", null, h("label", { for: "reply-draft" }, "A reply you can send")),
      h("p", { class: "hint", id: "reply-hint" }, "Fill in the parts in [brackets]. You can edit it here before copying."),
      area,
      h("div", { class: "btn-row mt" },
        h("button", { type: "button", class: "btn btn-small", onclick: () => onCopy?.(area, status) }, "Copy reply"),
        status)));
  }
  return block;
}
