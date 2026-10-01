# Plainly — build contract (source of truth for all builders)

> **Live mode is Option B (`AI_MODE=off`) since 1 Oct 2026.** The AWS account is on the Free account plan, which
> doesn't include Amazon Bedrock or Amazon Textract. The browser reads the letter (pdf.js text layer or Tesseract.js),
> the Lambda runs the rules reader, the verifier and template explanations, and nothing calls a model. The sections
> below describe the full design, including the Textract + Nova path that `AI_MODE=on` keeps. Where they disagree
> with [Option B](#option-b-ai_modeoff-1-oct-2026), Option B wins for the live product.

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
| unexpected_fee_to_release | strong (medium for a parcel) | a fee ("registration charges", "processing fee ... before release") standing between the reader and a prize, lottery win, refund or job. Parcel/customs fees are medium because real customs charges exist. "Refund of processing fee" doesn't count |
| link_bait | medium / strong | asks to click/open/scan a link or a button-like line ("Verify Your Identity Now") for a refund, payment, prize, or to verify/update details or KYC. No flag when every link it can mean is official (registry domain or government suffix). **Strong** when the link is a shortener/raw IP/free host/lookalike; when the claimed sender (registry agency named in the first 6 lines) links anywhere but its own site or hides the link; when a hidden link comes with a block/suspension threat; or when it says "reply Y / copy the link into your browser" (link-protection bypass). Button lines count only when the letter names no official site |
| callback_unofficial | medium / strong | asks to call/WhatsApp a number that isn't any registry agency's. Strong: a personal mobile (India 6-9xxxxxxxxx, UK 07) or WhatsApp link from a sender claiming to be an organisation, together with a cut-off threat; or any unofficial number with a cut-off threat and urgency_short. Medium: personal mobile alone, cut-off threat alone, or "if you did not make this payment, call ..." |
| kyc_update_threat | medium / strong | KYC/PAN/Aadhaar-link update demanded while the account/SIM "will be blocked/suspended/expire". Strong when the message sends you to a link or number to do it (link_bait, callback, risky link or personal mobile) |
| prize_or_refund_bait | medium / strong | prize/lottery/winner, unsolicited job ("CV has been selected", "daily salary", work from home + salary), cheap "scheme" loan (incl. Hindi लोन/ब्याज/माफ), or refund/credit you must click/verify/call/apply to receive (a refund notice that needs no action, or points to an official site/number, doesn't count). Strong when the only channel is a risky link, WhatsApp/Telegram, a personal mobile or free email |
| impersonation_mismatch | medium / strong | (a) a registry agency named in the first 6 lines, >=1 contact in the letter, none official (replaces unknown_contact in that case); (b) an email `From:` whose name claims a government body but whose address is not on a government/registry domain (GovDelivery allowed). Strong when the letter also asks for action through itself (link_bait, payment, credential, bait, callback, KYC, fee; for (b) also "verify your identity/details") |
| urgency_short | medium | act within < 72 h / "today" / "within 24 hours" / "immediately" / "tonight" / "blocked today" / "charged ... today" |
| freemail_official | medium | gmail/yahoo/outlook/hotmail/proton/rediffmail address presented as official contact |
| secrecy | medium | "do not tell", "keep confidential", "don't inform bank/family", "you have to maintain confidentiality" |
| shortened_or_raw_link | medium | a link on a shortener (bit.ly, tinyurl, surl.li, short.gy ...), a raw IP address, or a free web host (vercel.app, netlify.app, blogspot ...) |
| press_to_connect | medium | "press 1 to speak to an officer", "press 9 now" (language menus don't count) |
| unknown_contact | info (medium if agency matched) | phone/domain not in registry for the matched agency, next to at least one official contact — alone NEVER makes "likely scam" |
| injection_detected_model | info | model extract flagged instructions to AI |

Severity design: one warning sign never reaches 3 points on its own, and genuine wording (IRS "pay online at
www.irs.gov/payments", Income Tax "log in to the e-filing portal", bank alerts that say "never share your OTP") trips
none of the new rules (backend/tests/test_phishing_rules.py). The strong cases are combinations that genuine senders
don't use: an unofficial channel together with a lure, a block threat or an official name.

Verdict:
- score >= 3 -> `likely_scam`
- agency matched AND >=1 contact (domain or phone) matches registry AND score == 0 AND grounding ok -> `consistent_with_genuine`
- else -> `cant_tell`
Every rule appends a `trace` entry (flag/pass/unknown). Registry domains are matched first, phones second.
A domain listed for more than one agency, or a whole government suffix (gov.uk), never identifies an agency on its
own, and a bare mention of it ("GOV.UK" logo text) is not an official contact for `consistent_with_genuine`.
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
video_call [{quote}], ai_instructions [{quote}], link_requests [{quote}], callback_requests [{quote}],
account_verification_requests [{quote}], prize_or_refund_bait [{quote}], amounts [{amount, what, quote}], language_of_letter.
The four evidence lists only locate quotes: code re-checks each one (a link quote must mention a link and its host is
classified in code; a call-back quote must hold a phone number), and for these rules a quote the independent reader
never saw counts 0 points (`grounded: false`, severity info). Model quotes for credential_request must name a secret
the code recognises (so "enter the IP PIN" doesn't count), and a threat quote that tells the reader to report to the
police is ignored.
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
- `/judges/` 90-second guided tour: numbered steps, links straight to each sample result, criteria mapping.
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
  Its value and `IP_HASH_SALT` are random NoEcho stack parameters generated by `deploy.sh`, never the stack id.

## Review fixes (Sep 30, later)
- With an image and a Textract reading, `record_letter` is also asked for a `transcript` of text in a script the OCR
  missed (a Hindi body under an English letterhead). When it adds at least 20 non-Latin letters the OCR lacks, the
  rules run on OCR text + transcript, quotes are grounded only against the OCR part (non-Latin quotes count as
  unverified, `grounded: null`, not downgraded), and `grounding` gains `"partial": true, "unverified": n`. Such a
  letter can't be `consistent_with_genuine`.
- Fuzzy grounding has a 2 s total budget per check; after it only exact matches count. At most 4 model quotes are
  checked per rule.
- `credential_request` needs a hand-over verb (share, send, tell, give, reply with, read out...). "enter / verify /
  confirm / submit / update" count only when the sentence names no official site or portal; "e-verify" and "IP PIN"
  never count. Negation reaches over filler words ("will never ask you to share").
- A negated ask/demand/accept verb covers the whole comma list after it ("never demand ... a prepaid card, gift card or
  wire transfer"); an unrelated earlier "not" ("you did not respond ... a warrant") no longer hides a match.
- `payment_personal_upi`: a handle containing the sender's own name (from the letterhead when no agency matched) is
  skipped; a bare handle with no payment wording and no mobile number is medium, not strong.
- `/api/check` validates the request before counting it against the limits. IPv6 viewers are limited per /64.
- `/api/explain` clips every field of the client's `check` and rebuilds `verdict_label` from `verdict`; a `check`
  over 40,000 characters is a 400.
- Bedrock: each call's read timeout shrinks to fit the time left (3 s headroom); no call, including the first and the
  toolChoice retry, starts with under 6 s left. Textract makes one attempt.
- Sample results (`samples/results/<id>.json`, written by `scripts/run_samples.py`):
  `{id, title, image, mock, check: <check response minus letter_text>, explanations: {"English": <explain>, "Hindi": ..., "Spanish": ...}, generated_at}`.
  `build_site.py` prefers `samples/results/<id>.json` (live) and falls back to `samples/results/mock/<id>.json`
  (offline run); `--strict` refuses mock data. (Option B: the default `run_samples.py` run is the production
  AI_MODE=off path and writes `samples/results/<id>.json` with `"mock": false`; the old `results/mock/` files were
  deleted, and only `--ai-mock` writes there now.)
- PDFs are rendered 1100 px wide, up to 3 pages stacked (about 4300 px tall), still at most 1.5 MB; the server checks
  bytes, not pixels.

## Rules update (Sep 30, evening): links, lures and call-backs
- Tuned on `eval/dev/` (42 government-published examples: FTC, GOV.UK, PIB Fact Check, I4C, DoT, IRS) and the
  synthetic set; `eval/holdout/` was not consulted. Rules frozen afterwards: see `eval/RULES_FROZEN.md`.
- New rules: link_bait, shortened_or_raw_link, kyc_update_threat, prize_or_refund_bait, unexpected_fee_to_release,
  press_to_connect, callback_unofficial, impersonation_mismatch (table above).
- threat_arrest: "custody" only in a police/court sense ("into custody", "police custody"), so "invest under your
  custody" in an advance-fee email no longer counts. secrecy gains "you have to maintain confidentiality".
- `eval/run_eval.py --set dev|synthetic|holdout|all` (repeatable); each set is reported separately.

## False-positive hunt (Sep 30, night): genuine messages that read as scams
- 25 genuine messages written from public templates (IRS, SSA, USPS, HMRC, DVLA, SBI/HDFC, Income Tax, EPFO,
  e-Challan, India Post, TRAI, discoms, Passport Seva, I4C/DoT/police awareness texts, a US jury summons) were added
  as `eval/dev/genuine_fp_*.json`. Eleven were `likely_scam` when first run (eight under the rules frozen at 22:16,
  three more added after the first fixes); none is now. Regressions are in `backend/tests/test_false_positives.py`. `eval/holdout/` was not consulted. Rules re-frozen: see
  `eval/RULES_FROZEN.md`.
- Model quotes now get the code's own negation test: a quote in which every hit of the rule's pattern is negated
  ("Do not share OTP", "never ask you to transfer money to a 'safe account'", "Do not click on links") counts
  nothing. For `credential_request` the request verb must not be negated.
- Scam-awareness wording is reported speech, not a demand: in a sentence with "fraudsters", "scammers", "pretending
  to be", "posing as", "if you get a call saying ...", "if someone threatens ...", "it is a scam", "no such thing
  as", or "beware of ... fraud/digital arrest", matches for threat_arrest, video_call_demand, payment_gift_card,
  payment_crypto_wire, credential_request and urgency_short don't count, and a cut-off there is not a cut-off.
  Hindi negation after the verb ("गिरफ्तार नहीं करते", "कोई चीज़ नहीं होती") counts as negation.
- "officers never question or arrest anyone": a list of negated verbs joined by or/and is one negated action.
- threat_arrest: a match that denies itself ("CBI does not issue arrest ...") doesn't count; passport "police
  verification" / "forwarded to the police for verification" is not a threat; a model quote whose only police
  mention is the sender's name ("-Delhi Traffic Police") or police verification doesn't count. A threat stated as the
  consequence of not responding ("Failure to respond to this summons may result in ... a bench warrant") is medium
  when the letter has a real deadline (3+ days) and no urgency flag.
- Cut-off wording denied inside the match ("Your account will not be blocked") is not a cut-off.
- A model letter-date quote whose date is phrased as a deadline ("before 31-10-2026", "was due on 31 July 2026") is
  not taken as the letter's date (the code's own finder already skipped such dates), so SMS with one date no longer
  get urgency_short from a 0-day gap.
- `.bank.in` (open only to RBI-regulated banks) and `.sbi` count as official hosts, like `.gov.in`.
- A message that also offers "visit your (nearest/home) branch" keeps link_bait for a hidden link at medium, and
  kyc_update_threat is not raised to strong by that link (short links and personal mobiles still make it strong).

## Option B (AI_MODE=off, 1 Oct 2026)

Why: the owner's account is on the AWS Free account plan. On 30 Sep at 22:16 IST, Bedrock `Converse` returned
`ValidationException ... Operation not allowed` for every Nova model tried, and Textract `DetectDocumentText` returned
`SubscriptionRequiredException ... The AWS Access Key Id needs a subscription for the service`. The owner can't upgrade,
so the live product runs on Free-plan services only (Lambda, API Gateway HTTP API, CloudFront, S3, DynamoDB,
CloudWatch, SNS, Budgets). The Textract + Nova path stays in the repo and comes back with `AI_MODE=on`.

### Switch
- Lambda env `AI_MODE` = `off` (default) | `on`. CloudFormation parameter `AiMode`, default `"off"`, sets it.
- `off`: no boto3 `bedrock-runtime` or `textract` client is ever created, and the Lambda role has no Bedrock or
  Textract statements (they are added only under the template's `AiOn` condition).
- `on`: the design in the sections above, unchanged.

### Reading happens on the device
- Photos: the browser downscales to about 2000 px on the long edge, converts to grayscale and runs Tesseract.js
  (self-hosted under `/vendor/tesseract/`, languages `eng` + `hin`). The photo never leaves the device.
- PDFs: pdf.js `getTextContent` on up to 3 pages first. With at least 80 characters of real text, that text is used and
  OCR is skipped. Otherwise the pages are rendered to canvas and OCR'd.
- The recognised text appears in an editable box ("check the text matches your letter; fix anything misread") and is
  sent only when the user presses Check.
- If OCR fails, the page asks the user to paste the text.

### POST /api/check (off)
Request:
```json
{ "text": "the letter text (required)",
  "text_source": "typed" | "device_ocr" | "pdf_text" | "sample_text",
  "today": "YYYY-MM-DD (optional)" }
```
- `image` is rejected with 400 and a friendly message saying the page reads photos on the device.
- Text over 30,000 characters is refused with a friendly 400 (`MAX_DEVICE_TEXT_CHARS` in `pipeline.py`).
- Extraction is done by the production rules reader `backend/reader.py`: the keyword and date reader that the frozen
  offline eval measured (`eval/mock_model.py`), moved into the backend unchanged. Then the same `verifier.py` rules,
  registry match and date math run as before.
- `grounding.source` follows `text_source`: `typed` -> `"pasted_text"`, `device_ocr` -> `"device_ocr"`, `pdf_text` ->
  `"pdf_text"`. Quotes come from the text itself, so grounding is exact by construction; it proves only that the quote is in the text the user sent.
- The server trace starts at the reader step. The device's reading step is shown by the page, not the server trace.
- `meta.model` is `"rules-v<hash prefix>"`; token counts are 0.
- Response shape is otherwise identical to the contract above.

### POST /api/explain (off)
- Same request and response shape. No model: `backend/explain_templates.py` builds the answer from fixed,
  pre-written strings (drafted with the coding agent, no native-speaker review yet), per verdict (tldr, 3 to 5 points) and per flagged rule (what it means, what to do).
- Standard actions: `likely_scam` = don't pay, don't call or click anything in the message, call the official number
  shown, report it through the country's channel. `consistent_with_genuine` = still confirm on the official number, pay
  only through the official site, add the deadline to the calendar. `cant_tell` = how to check it yourself.
- `jargon` comes from a glossary of common official-letter terms (notice, arrears, penalty, KYC, PAN, TDS, lien,
  appeal and so on) found in the letter text. `reply_draft` is `""` for `likely_scam`; otherwise a polite template
  (confirm the notice, ask for a payment plan or more time) filled from the extracted sender, date and amounts.
- Deadlines come from the verified `check`. Nothing does date math except `dates.py`.
- Languages: English, Hindi (हिन्दी) and Spanish, all written out. Any other requested language gets English with
  `meta.fallback_language: true`.

### GET /api/health (off)
`{"ok": true, "version": "...", "ai_mode": "off"}`

### Headers the site needs
Tesseract runs a Web Worker and WebAssembly, so any Content-Security-Policy must allow `worker-src 'self' blob:` and
`script-src 'self' 'wasm-unsafe-eval'`. `.wasm` files are served as `application/wasm`; the `.traineddata.gz` language
files as `application/octet-stream` without a `Content-Encoding` header (Tesseract unzips them itself).

### Review fixes (1 Oct 2026, Option B)
- `text_source` `"sample_text"` -> `grounding.source` `"sample_text"` ("the sample letter's text"). Only
  `scripts/run_samples.py` sends it: the showcase results are computed from `samples/letters/<id>.txt`, transcribed
  from the HTML, not read from a photo, so they must not claim a device reading. On-device Tesseract does not read the
  faint line in `ai-instruction.png`; the site says so.
- `/api/explain` request gains optional `"today": "YYYY-MM-DD"` (validated like `/api/check`'s, else the server's
  date). Deadlines before it get past-tense wording ("Date already passed"), no "Add to calendar" step, a "what
  should I do now" question and a reply that says the date has passed.
- With AI off, `/api/explain` accepts a `check` of up to 100,000 characters (`MAX_CHECK_CHARS_OFF`; 40,000 with AI
  on) and keeps up to 30,000 characters of `letter_text`, so any check `/api/check` accepted can be explained.
- Explain rate limit: `EXPLAIN_RATE_LIMIT_PER_HOUR`, default 5 x `RATE_LIMIT_PER_HOUR` with AI off (templates cost
  nothing; each language switch asks for one), equal to it with AI on. `EXPLAIN_DAILY_CAP` default 10 x `DAILY_CAP`
  off, 2 x on. The page also caches explanations per result, language and level.
- Template actions: the verdict's standard steps are always kept. `cant_tell`: standard steps first, then at most 3
  deadlines, then flag steps. `consistent_with_genuine`: "Confirm with <agency> first", then at most 3 deadlines,
  then the other standard steps. `likely_scam`: standard steps, then flag steps, leaving out `unknown_contact` and
  `injection_detected_model` (they would contradict "don't call or click anything in it").
- Reply draft addressee: the matched agency's name, else `claimed_sender` only when it reads like a name (60
  characters or fewer, 8 words or fewer, no run of 3+ digits, no sentence punctuation, no greeting or headline
  opener); otherwise "The office that sent the notice". A one-line SMS (which can hold an OTP) is never the
  addressee.
- The explanation templates are fixed, pre-written text drafted with the coding agent. The site and docs say so, and
  say that the Hindi and Spanish have not had a native-speaker review; never describe them as written by people.
