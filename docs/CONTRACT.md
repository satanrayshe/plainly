# Plainly — build contract (source of truth for all builders)

Product: **Plainly — Is this letter real?** Upload a photo/PDF/screenshot of an official-looking letter, SMS or email
(or paste its text). Plainly returns a verdict — **Likely scam / Consistent with a genuine <agency> letter — confirm on
the official number / Can't tell** (never "safe") — with every red flag quoted from the letter and checked in code, a
"receipts" trace of every check, then a plain-language explanation in the reader's language, real deadlines (.ics),
and a reply draft (only when not a likely scam).

Primary persona: families handling official mail in a second language, India + US (UK secondary).
Hackathon: AWS "Zero to Shipped", category #daily-life-enhancement, lane #startups. Region **us-east-1**.

## Repo layout
```
backend/            Lambda (Python 3.13, arm64, boto3 only — NO third-party deps)
  app.py            handler + routing (existing; refactor, keep respond/rate-limit style)
  pipeline.py       ocr() -> extract() -> verify() ; narrate()
  verifier.py       deterministic rules, registry matching, date math, verdict, trace
  registry.json     official agency contacts (domains first, phones second), each with source_url + checked_on
  bedrock.py        Converse wrapper: model fallback chain, timeouts, tool-forcing, usage capture
  tests/            pytest (verifier + grounding + dates + routing, Bedrock/Textract mocked)
infra/
  template.yaml     plain CloudFormation (no SAM transform)
  cf-function.js    CloudFront Function: URI rewrite (/path -> /path/index.html)
scripts/
  deploy.sh         bash (Git Bash on Windows OK): package lambda zip, cfn package/deploy, s3 sync, invalidate
  build_site.py     renders site/ templates + samples/*.json into dist/ (pre-baked sample results in HTML)
  render_letters.py renders samples/letters/*.html -> PNG via headless Edge/Chrome
  run_samples.py    runs the real pipeline on sample letters -> samples/results/<id>.json (needs AWS creds)
site/               static source (vanilla HTML/CSS/JS, no framework, no build tooling beyond build_site.py)
samples/
  letters/          synthetic showcase letters as HTML (+ rendered PNG), every one watermarked
                    "SAMPLE — NOT A REAL NOTICE", no seals/logos, no real PII
  results/          pre-computed pipeline output JSON per sample (filled after AWS connect)
eval/
  holdout/          real government-published scam examples (text transcriptions) with source URLs + labels
  synthetic/        generated labeled letters
  run_eval.py       runs pipeline, writes eval/results.md (synthetic and holdout reported SEPARATELY, misses listed)
docs/
  agent-log.md      timestamped build log (agent did / human decided / evidence)
  SUBMISSION.md     Builder Center write-up draft
```

## HTTP API (all JSON, same origin via CloudFront, prefix /api)

### POST /api/check
Request:
```json
{ "image": {"type": "image/jpeg", "data": "<base64>"} | null,
  "text": "optional pasted text (SMS/email/letter)",
  "today": "YYYY-MM-DD (client local date, optional)" }
```
- Client downscales images to <= 1.5 MB JPEG (max 2000px long edge); PDFs rendered client-side with pdf.js,
  first <= 3 pages stacked vertically into ONE JPEG. Server rejects base64 payload > 2.2 MB with 400.
- Server budget: total <= 25 s. Textract ~2-4 s, extract call read_timeout 14 s, at most 1 retry, skip fallbacks when
  `context.get_remaining_time_in_millis() < 8000`.

Response 200:
```json
{
  "verdict": "likely_scam" | "consistent_with_genuine" | "cant_tell",
  "verdict_label": "Likely scam",
  "headline": "short human sentence",
  "agency": {"key": "irs", "name": "Internal Revenue Service", "country": "US",
             "official_phone": "800-829-1040", "official_site": "https://www.irs.gov",
             "report_channel": {"name": "FTC", "url": "https://reportfraud.ftc.gov"},
             "source_url": "...", "checked_on": "YYYY-MM-DD"} | null,
  "flags": [ {"rule": "payment_gift_card", "severity": "strong"|"medium"|"info",
              "title": "Asks for payment by gift card",
              "quote": "exact text from the letter" | null,
              "quote_redacted": false,
              "grounded": true|false|null,          // quote found in independent OCR text?
              "why": "one plain sentence", "source": {"name": "FTC", "url": "..."} } ],
  "trace": [ {"step": "ocr", "status": "done"|"skipped"|"failed", "detail": "Textract read 41 lines", "ms": 1830},
             {"step": "extract", ...}, {"step": "rule:payment_method", "status": "flag"|"pass"|"unknown", "detail": "...", "ms": 0}, ... ],
  "extracted": { "claimed_sender": "...", "letter_date": "YYYY-MM-DD"|null,
                 "phones": ["..."], "urls": ["..."], "emails": ["..."], "amounts": ["..."],
                 "deadlines": [{"date": "YYYY-MM-DD", "what": "...", "quote": "...", "computed_from": "letter_date + 30 days"|null}] },
  "letter_text": "OCR text (Textract) or pasted text; used by /api/explain; never stored",
  "grounding": {"source": "textract"|"pasted_text"|"none", "grounded": 7, "total": 8},
  "meta": {"model": "us.amazon.nova-2-lite-v1:0", "ms": 6400, "input_tokens": 0, "output_tokens": 0}
}
```

### POST /api/explain
Request: `{ "letter_text": "...", "check": <the /api/check response minus letter_text>, "language": "English"|"Hindi"|"Spanish"|free text (<=40 chars), "level": "simple"|"normal" }`
Response 200:
```json
{ "language": "Hindi",
  "tldr": "1-2 sentences",
  "explanation": ["3-6 plain points"],
  "actions": [{"step": "...", "how": "...", "by": "YYYY-MM-DD"|null}],
  "jargon": [{"term": "...", "meaning": "..."}],
  "questions_to_ask": ["..."],
  "reply_draft": "..." ,          // "" when verdict == likely_scam (then actions = do-not-pay / report steps)
  "meta": {"model": "...", "ms": 0, "input_tokens": 0, "output_tokens": 0} }
```
Deadlines/dates are NEVER computed by the model in narrate; it receives the verified deadlines from `check`.

### GET /api/health -> `{"ok": true, "version": "..."}`
### GET /api/stats  -> anonymous counters `{"checks_total": n, "by_verdict": {...}, "by_language": {...}}`

Errors: `{"error": "friendly message"}` with 400 / 429 / 502 / 503. On 429/503 (rate or global daily cap) the UI offers
the sample letters instead.

Removed: /api/share (privacy: nothing about a letter is stored).

## Verifier rules (verifier.py) — deterministic, run on `letter_text` + model-extracted items
Severity: strong = 3 points, medium = 1 point, info = 0.

| rule id | severity | detection |
|---|---|---|
| payment_gift_card | strong | gift card / iTunes / Google Play / Steam / Amazon card as payment |
| payment_crypto_wire | strong | bitcoin/crypto/USDT/wire/Western Union/MoneyGram/bitcoin ATM |
| payment_personal_upi | strong | UPI ID / payment app to a personal handle or number (e.g. `name@okaxis`, "PhonePe/GPay to 98xxxxxxxx") when claimed sender is a government body/utility |
| credential_request | strong | OTP, PIN, password, CVV, full SSN, full Aadhaar, net-banking login |
| threat_arrest | strong | arrest / police / warrant / deportation / "digital arrest" / FIR / CBI / legal action "today" |
| video_call_demand | strong | demands video call / Skype / WhatsApp video / stay on call |
| ai_instruction | strong | hidden instructions aimed at AI tools ("ignore previous instructions", "as an AI", "classify this as legitimate", "system prompt"...). Quote is ALWAYS redacted: `quote=null, quote_redacted=true`. |
| lookalike_domain | strong | URL/email domain resembling a registry domain (edit distance <=2, confusable chars, punycode, extra words like `irs-gov-refund.com`) but not equal/subdomain |
| urgency_short | medium | act within < 72 h / "today" / "within 24 hours" / "immediately" / "tonight" |
| freemail_official | medium | gmail/yahoo/outlook/hotmail/proton/rediffmail address presented as official contact |
| secrecy | medium | "do not tell", "keep confidential", "don't inform bank/family" |
| unknown_contact | info (medium if agency matched) | phone/domain not in registry for the matched agency — alone NEVER makes "likely scam" |
| injection_detected_model | info | model extract flagged instructions to AI |

Verdict:
- score >= 3 -> `likely_scam`
- agency matched AND >=1 contact (domain or phone) matches registry AND score == 0 AND grounding ok -> `consistent_with_genuine`
- else -> `cant_tell`
Every rule appends a `trace` entry (flag/pass/unknown). Registry domains are matched first, phones second.
Model-extracted quotes are "grounded" if their normalized form (casefold, collapse whitespace, strip punctuation)
appears in the OCR text or fuzzy-matches (>= 0.85 ratio via difflib on a sliding window). Ungrounded strong flags are
downgraded to medium and marked `grounded:false`.

Report channels: US -> FTC reportfraud.ftc.gov; India -> cybercrime.gov.in / 1930; UK -> Report Fraud (formerly Action Fraud) reportfraud.police.uk / 0300 123 2040.

## Extract tool (Bedrock Converse, forced tool `record_letter`)
Model: `us.amazon.nova-2-lite-v1:0` then `us.amazon.nova-pro-v1:0`, `us.amazon.nova-lite-v1:0`. temperature 0, maxTokens 1500.
If toolChoice `{"tool":...}` is rejected, retry with `{"any":{}}`; last resort JSON-in-text via parse_json.
Input: image (if any) + `letter_text` (OCR) as text. Tool fields: claimed_sender, claimed_agency_key (one of registry keys
or "other"), country, letter_date {value, quote}, deadlines [{quote, absolute_date|null, relative_days|null, relative_to:"letter_date"|"receipt"|null, what}],
payment_requests [{method, quote}], threats [{quote}], credential_requests [{quote}], secrecy [{quote}],
video_call [{quote}], ai_instructions [{quote}], amounts [{amount, what, quote}], language_of_letter.
Regex (code, not model) extracts phones/urls/emails from letter_text; model lists are merged only if grounded.

## Frontend pages (site/)
- `/` landing: hero "Is this letter real?"; three side-by-side sample tiles (electricity FINAL NOTICE scam, IRS-style
  genuine-format notice, "digital arrest"/customs-parcel scam) whose results are PRE-RENDERED into the HTML by
  build_site.py (no JS needed to read them). CTA "Check your own letter" -> /try/. Works with JS disabled.
- `/try/` upload (drag/drop, camera capture on mobile, PDF via pdf.js vendored at /vendor/pdfjs/), paste text,
  language select (English, हिन्दी, Español, other…), results: verdict banner, quoted flags, receipts panel,
  official number box ("Do not call the number on this letter. Official line: X (source)"), then explanation,
  deadlines with "Add to calendar" (.ics generated client-side), reply draft w/ copy button. Also sample tiles
  including the AI-instruction sample (image only, neutral alt text).
- `/how-it-works/` pipeline diagram (inline SVG), the rules table, privacy (nothing stored), limitations.
- `/evidence/` text mirror of the agent-connection proof (filled after AWS connect; placeholder sections now).
- `/judges/` 60-second guided tour: numbered steps, links straight to each sample result, criteria mapping.
- Design: warm "paper & ink" editorial look — off-white paper, near-black ink, one signal red for scam, one calm
  green-teal for consistent, amber for can't tell; serif display headings (e.g. "Fraunces" or "Newsreader" self-hosted
  or system serif fallback), readable 18px body; generous line height; WCAG AA contrast; big tap targets (elderly users);
  no gradients-for-the-sake-of-it, no emoji icons, no generic AI-slop hero. Mobile-first.
- Every page: <title>, meta description, Open Graph tags, footer "Not legal advice. Plainly never stores your letter."

## Privacy / safety
- Never store letter content or results. Logs are structured JSON with NO letter text (only ids, verdict, rule ids, ms, tokens).
- Rate limit: per-IP from `CloudFront-Viewer-Address` header (fallback requestContext.http.sourceIp), 20/hour;
  global daily cap 400 checks in DynamoDB -> 503 with sample fallback.
- Injection text never rendered anywhere (UI, docs, write-up).

## Additions made during integration (Sep 30)
- `/api/check` also returns a top-level `report_channel` (chosen by country) because `agency` is null when no agency
  matches. The UI uses `agency.report_channel`, then `report_channel`, then a fixed list of the three channels.
- `record_letter` has a `transcript` field, filled only when OCR reads under 40 characters (e.g. Hindi letters). Then
  grounding source is `"none"`, every flag's `grounded` is null, and the verdict can't be `consistent_with_genuine`.
- `/api/stats` also returns `explains_total`; `by_language` buckets are english / hindi / spanish / other.
- CloudFront sends `x-origin-verify`; the Lambda answers 403 when it doesn't match `ORIGIN_VERIFY` (unset locally).
- Sample results (`samples/results/<id>.json`, written by `scripts/run_samples.py`):
  `{id, title, image, mock, check: <check response minus letter_text>, explanations: {"English": <explain>, "Hindi": ..., "Spanish": ...}, generated_at}`.
  `build_site.py` prefers `samples/results/<id>.json` (live) and falls back to `samples/results/mock/<id>.json`
  (offline run); `--strict` refuses mock data.
- PDFs are rendered 1100 px wide, up to 3 pages stacked (about 4300 px tall), still at most 1.5 MB; the server checks
  bytes, not pixels.
