# Build brief: "Plainly — Is this letter real?" (Zero to Shipped, as of 30 Sep 2026)

## 1. Decision and why it wins

**Pick: keep Plainly, but put the scam check first.** This merges C1 and C16, with one element from C13:
- **C1** supplies the fake-vs-genuine side-by-side, the prompt-injection tile, and dates computed in code.
- **C16** supplies the visible "receipts" trace for every check, and the line "two agents, both leave receipts".
- **C13** supplies one element only: every flag quotes the exact line of the letter it came from.

**Rejected:**
- **Payhold (C10).** It has the best originality score (8.0), but it is a domain pivot with RDAP/DNS flakiness. Feasibility is 6.5, and a solo builder has about 65 hours.
- **AgentCore, Nova Sonic and Nova Act.** Too risky for the time available. They go in the roadmap.

**The gap it fills.** None of the 150 published projects mentions scams, phishing, fraud or impersonation. The document explainers in the field (OBLIGRA, BillShield, LexiGuide, NoticeLens) all assume the letter is genuine.

**Fit to each official criterion (Rules: four criteria at 25% each, same at Gate 1 and Gate 2):**

| Criterion | How this entry scores | Judges it lands with |
|---|---|---|
| Technical Innovation & Originality | - Code decides the verdict; the model only reads and explains. It never says "safe".<br>- Every quote the model cites is checked against its own transcript.<br>- Instructions hidden in a letter and aimed at AI tools are detected and treated as a scam signal.<br>- Every check leaves a visible trace. | Bhavin: his "verify its thought process" writing and calculator-tool example. Raghuram: running agents safely. |
| Implementation Quality | - Whole stack in one IaC template, least-privilege roles, no letters stored.<br>- Rate limits, budget, CloudWatch dashboard and alarms.<br>- pytest suite, plus a 24-letter evaluation with published metrics.<br>- "Gotchas" section with the exact error text. | Manuela (IaC, testing, security), Abdullah (TAM work: observability, operations), Hamza (a production-shaped serverless build). |
| Community/Market Impact | - Verified FTC, FBI IC3 and India MHA/I4C figures.<br>- Measured cost per letter.<br>- A B2B2C path: credit unions, legal aid, immigrant-services groups, telcos. | Bhavin and Raghuram, the two Startups SAs. |
| Creativity & Storytelling (and the About tab's "communication quality") | - Two letters that look alike get opposite verdicts, with every claim sourced.<br>- The build agent ran under a policy that forbids it from deleting things or switching off the audit log, and CloudTrail proves it. The product applies the same "trust, then verify" idea to your mail. | Everyone, including the AI scorer. |

**Category: #daily-life-enhancement.**
- About 11 tagged competitors, against 24 in social-good.
- Fraud falls outside Social Good's three focus areas (Education, Health, Climate).
- "5 winners across the app categories" makes a less crowded category worth more.

**Lane: #startups (plural, confirmed by the organizer).**
- Two of the five judges are Startups Solutions Architects.
- There is a credible wedge: free for consumers, paid white-label for organizations that already get "is this real?" calls every day.

**Remaining tag slots:** #amazon-bedrock, #aws-lambda, #security.

## 2. Product scope

### Must-have: this is the killer demo
1. **Landing page (static, no login, readable without JS).**
   - Two tiles side by side: "Electricity FINAL NOTICE" (a synthetic scam) and "IRS CP14-style notice" (synthetic, in genuine format). Results are pre-baked into the HTML.
   - A third tile: a letter containing hidden instructions aimed at AI tools.
2. **Verdict banner.** Exactly three states: **Likely scam / Consistent with a genuine [agency] letter: confirm on the official number / Can't tell**. "Safe" is never an output.
3. **Red flags from deterministic Python rules.** Each flag carries the quoted line and a source.

   | # | Rule |
   |---|---|
   | 1 | Payment by gift card, crypto, wire, or UPI/payment app to a personal ID (FTC: only scammers ask for gift cards) |
   | 2 | Threat of arrest, police or deportation |
   | 3 | Less than 72 hours to act |
   | 4 | Phone number not in the official registry for the claimed agency |
   | 5 | Link not on the agency's domain: lookalike (edit distance, confusable characters, punycode) or not .gov |
   | 6 | Free-mail address (gmail and similar) given as an official contact |
   | 7 | Request for an OTP, PIN, password, full SSN or Aadhaar number |
   | 8 | Secrecy demands |
   | 9 | "Digital arrest" or a demanded video call |
   | 10 | Hidden instructions aimed at AI tools |

4. **Official-contacts registry.** About 20 agencies (IRS, SSA, USCIS, Medicare, HMRC, DVLA, CRA, Income Tax Dept, UIDAI, EPFO, e-challan/Parivahan, and 3 to 4 electricity distribution companies). Each entry has a source URL and a "checked on" date.
   - Scam verdicts show **"Do not call the number on this letter. Official line: X (source)"** plus the right reporting channel: reportfraud.ftc.gov, cybercrime.gov.in / 1930, or Action Fraud.
5. **Receipts panel.** The ordered list of checks with FLAG / PASS / UNKNOWN. It is rendered from a returned `trace[]`, not streamed.
6. **Plain-language explanation** in English, Hindi or Spanish (a free-text language field is also allowed).
   - Actions and deadlines. Relative deadlines ("within 30 days of this notice") are computed in Python from the quoted notice date.
   - "Add to calendar" button that downloads an .ics file.
   - A reply draft, only when the verdict is not "Likely scam".
7. **Upload path.** Photo or PDF, downscaled in the browser to 1.5 MB or less. The letter is processed in memory and never stored.
8. **Static pages:** `/how-it-works`, `/evidence` (mirrors the agent proof as text) and `/judges` (a 60-second click-through tour).

### Nice-to-have, in priority order, only after milestone M1
1. Bedrock Guardrails `ApplyGuardrail` prompt-attack check as a second layer behind the regex. Timebox: 45 minutes.
2. CloudWatch Synthetics canary on the public URL every 30 minutes through Oct 26 (about $1). This is insurance for the ship gate.
3. Amazon Textract `DetectDocumentText` as an independent OCR that confirms each quoted line ("two independent readers").
4. A live anonymous counter of verdicts and languages.

### Explicit cuts
- AgentCore (Harness, Web Search, Memory).
- Nova 2 Sonic voice.
- Nova Act.
- Accounts or login.
- Bounding boxes drawn on the image.
- Lambda durable-function reminders (the .ics replaces them).
- The share feature. The code stays in place but is disabled, because the existing version keeps letter summaries for 7 days.

## 3. AWS architecture (us-east-1, deployable from Windows)

```
Browser ──> CloudFront ─┬─ default ─> S3 (private, OAC): static pre-rendered HTML + samples + demo.mp4
                        └─ /api/*  ─> API Gateway HTTP API (stage throttle 5 rps / burst 10)
                                         └─> Lambda py3.13 arm64 1024MB 29s
                                               1 extract   Bedrock Converse, Nova 2 Lite, forced tool call (fields + quotes + transcript)
                                               2 verify    pure Python rules + registry.json + date math + quote-grounding
                                               3 narrate   Bedrock Converse in the chosen language (explanation, actions, reply)
                                               ├─> DynamoDB on-demand, TTL: per-IP limits, sample cache, anonymous counters
                                               └─> CloudWatch: JSON logs (no letter text), dashboard, alarms -> SNS email
Account-level: CloudTrail trail (management events + AWS MCP data events -> S3 + CloudWatch Logs), AWS Budgets $10
```

**Why each service:**
- **CloudFront + OAC.** One stable AWS URL and a private bucket.
- **HTTP API, not a Function URL.** Built-in throttling. It also avoids the OAC signing problem on POST: a Lambda URL behind OAC needs an `x-amz-content-sha256` header.
- **The existing handler already reads the v2 event format** (`rawPath`, `requestContext.http`), so it works unchanged.
- **Nova 2 Lite.** Active, handles image input and tool calling, and costs very little.

**Deployment:**
- One SAM-transform template, deployed with `aws cloudformation package` then `aws cloudformation deploy`. No Docker or SAM CLI is needed on Windows. Use `sam deploy` if SAM is already installed.
- Lambda has zero third-party dependencies (boto3 only). PDFs are rendered to images in the browser with pdf.js, unless the smoke test shows a document block works.

**Cost:**

| Item | Estimate |
|---|---|
| Nova 2 Lite, per letter | About 4.5k input + 2k output tokens at the third-party price of $0.30/$2.50 per 1M, so about $0.006. Measure it from the Converse `usage` fields and publish the measured figure. |
| Textract (optional) | +$0.0015 per page |
| Lambda, DynamoDB, CloudFront, S3 | Pennies or free tier |
| CloudTrail data events | About $0.10 per 100k |
| Canary | About $1 |
| **Total through Oct 26** | **Under $5.** Budget alert at $10. |

**Fallbacks:**
- **Model chain:** `us.amazon.nova-2-lite-v1:0` (the in-Region ID fails; use the `us.` profile), then `us.amazon.nova-pro-v1:0` / `us.amazon.nova-lite-v1:0` if `get-foundation-model` still shows them ACTIVE, then cached sample results.
- **Forced tool choice rejected:** use `toolChoice:any` with a single tool, then fall back to the existing `parse_json` path.
- **Reserved concurrency:** skip it. New accounts often have a Lambda concurrency limit of 10, and reserving any would fail. HTTP API throttling, the per-IP DynamoDB limit and the budget cover this instead.
- **Bedrock throttled or quota too low:** judges' sample tiles never call Bedrock, and live uploads show a friendly retry message.

## 4. Hour-by-hour plan (IST; deadline Oct 3 12:29 IST = Oct 2 11:59 PM PDT)

**Sep 30**

| Time | Work |
|---|---|
| 19:30–20:30 | Agent connection (section 5, steps 1–3). Save the text transcript. |
| 20:30–21:15 | Through MCP, the agent creates the CloudTrail trail (with MCP data events, to S3 and CloudWatch Logs), the SNS topic and the $10 Budget. Check that the events appear. |
| 21:15–22:30 | Bedrock smoke tests: Nova 2 Lite with an image, forced tool choice, the PDF document block, v1 model status. Log the exact errors for the Gotchas section. Decide the PDF path. |
| 22:30–00:30 | Agent writes the template (S3+OAC, CloudFront, HTTP API, Lambda from the existing app.py, DynamoDB TTL, 7-day log retention) and deploys it. Static placeholder landing page with real text. Check with `curl`. |
| 00:30–01:00 | **Shrey creates and PUBLISHES the Builder Center project:** title, description, 5 tags, live URL, a short body with the proof so far. |
| 01:00–07:30 | Sleep. |

**Oct 1**

| Time | Work |
|---|---|
| 07:30–10:30 | Refactor into `extract()` → `verify()` → `narrate()`. Tool schema: sender, claimed agency, letter date, phones, URLs, emails, amounts, dates, payment methods, threats, each with its quote, plus the transcript. Add the quote-grounding check. |
| 10:30–13:30 | `verifier.py`: registry (agent drafts it; **Shrey checks every number against its source URL**), 10 rules, verdict logic, date math, .ics. About 30 pytest tests. |
| 13:30–14:15 | Break / buffer. |
| 14:15–16:30 | Narration in the chosen language. Reply draft vs report channel. Response `trace[]`. |
| 16:30–19:30 | `/try` UI: tiles, banner, receipts panel, quoted flags, deadlines and .ics, language toggle, upload with downscaling and pdf.js. |
| 19:30–20:30 | 6 synthetic showcase letters (HTML rendered to PNG with headless Edge; no real logos, no real PII). Pre-compute results and bake them into the landing HTML. |
| 20:30–21:30 | **M1: core live.** Test from a phone off Wi-Fi and with `curl` (no JS). Update the Builder Center project. |
| 21:30–23:30 | Guardrails layer, per-IP limit, API throttle, dashboard and alarms (created through MCP for the evidence). Capture one real incident the agent diagnosed from CloudWatch Logs. |
| 23:30–00:30 | Agent writes the generator for the 24-letter eval set (12 genuine-format, 12 scam variants) and its labels. |
| 00:30–06:30 | Sleep. |

**Oct 2**

| Time | Work |
|---|---|
| 06:30–08:30 | Run the eval, fix the worst failures, re-run. Write `eval/results.md`. |
| 08:30–10:00 | Canary first, then Textract cross-check only if on schedule. |
| 10:00–12:00 | `/how-it-works` (SVG diagram), `/evidence`, `/judges`, Open Graph and meta tags, noscript path. |
| 12:00–13:00 | 3 to 5 real people (family) try it. Write down their honest quotes and the n. |
| 13:00–16:00 | Draft the write-up in `docs/SUBMISSION.md` and paste it into Builder Center. |
| 16:00–17:30 | Final proof package (section 5). |
| 17:30–19:00 | Record the 90-second video, host it at `/demo.mp4` on CloudFront, embed it and link it. |
| 19:00–20:00 | Cover image (1200x675, no text) and architecture PNG. |
| 20:00–23:30 | Buffer and fixes. **M2: submission complete by 23:30 IST** (Oct 2 11:00 AM PDT). |
| 23:30–06:00 | Sleep. |

**Oct 3**

| Time | Work |
|---|---|
| 06:00–10:00 | Check everything from a signed-out browser: tags, links, `curl`, the evidence page. |
| **10:00** | **Freeze.** That leaves 2.5 hours of buffer. |

**After the deadline:** don't touch the stack. Keep it live until at least Oct 26 and check it daily Oct 5–19.

## 5. Agent connection proof and documentation

**Proof steps:**
1. **Dedicated console IAM user `plainly-agent`.**
   - Permissions: `SignInLocalDevelopmentAccess` plus a scoped policy covering CloudFormation, Lambda, S3, CloudFront, API Gateway, DynamoDB, Bedrock invoke, Logs, CloudWatch, Budgets, SNS, CloudTrail, and `iam:*Role*`/`PassRole` limited to `plainly-*`. Region locked to us-east-1.
   - Explicit **Deny** when `aws:ViaAWSMCPService` is true on: `cloudtrail:StopLogging`, `cloudtrail:DeleteTrail`, `cloudformation:DeleteStack`, `s3:DeleteBucket`, `dynamodb:DeleteTable`, `iam:Delete*`, `iam:CreateAccessKey`.
   - Keep the deny list to named actions. A blanket `Delete*` might break CloudFormation replacements.
   - Timebox: 45 minutes. If it fights you, use broader permissions but keep the deny, and say so in the write-up.
2. **Connect Claude Code:**
   - `aws login --region us-east-1 --profile plainly-agent`
   - `aws sts get-caller-identity --profile plainly-agent`
   - `aws configure agent-toolkit --yes --region us-east-1 --profile plainly-agent`
   - Set `AWS_MCP_PROXY_PROFILES=plainly-agent` in the Claude Code MCP config.
   - Restart, check `/mcp` shows aws-mcp connected, then ask "What AWS Regions are available?"
3. **Capture as text code blocks** (screenshots too, but keep text copies, because moderation has rejected images):
   - the MCP config snippet
   - the configure output
   - masked `sts get-caller-identity`
   - one `describe`/`get` call by the agent through MCP on the deployed Lambda and distribution, with request IDs and timestamps
4. **Route a few write actions through MCP on purpose** (trail, budget, alarms, dashboard) so CloudTrail shows `aws-mcp.amazonaws.com` / `CallReadWriteTool`.
   - Note: `aws cloudformation deploy` run from the agent's shell is a CLI call, not an MCP call. Say that honestly.
   - Screenshot a CloudWatch Logs Insights query of the trail filtered on `eventSource = aws-mcp.amazonaws.com`.
5. **Git evidence.** Public repo on **satanrayshe**, using the global git identity only. Commits carry the Claude co-author trailer.

**README / write-up headings, in order:**
1. TL;DR, live URL, "Try in one click", video
2. The problem
3. What I shipped
4. **Technical Innovation & Originality**
5. **Implementation Quality**
6. **Community/Market Impact**
7. **Creativity & Storytelling**
8. How the coding agent helped me ship: a table with columns *agent did / I decided / evidence*
9. Proof of coding agent connection to the AWS console
10. Architecture on AWS: diagram, service table, cost per letter
11. Evaluation results
12. Gotchas we hit (exact errors, e.g. the Nova in-Region model-ID error)
13. Limitations
14. Where it's headed (Startups)
15. Category & lane

**Build log:** `docs/agent-log.md`, with timestamped transcript excerpts and the incident where the agent read CloudWatch Logs through MCP and fixed the bug.

**90-second video script:**

| Time | Scene |
|---|---|
| 0–10 s | The two letters side by side: "One is real. One will empty your account." |
| 10–35 s | Click the fake letter. Red banner, quoted flags, receipts panel, "call this official number instead". |
| 35–55 s | Click the genuine one. "21 days left", .ics download, switch to Hindi. |
| 55–65 s | The injection letter is caught. |
| 65–85 s | Architecture, then the CloudTrail MCP events, then the deny policy: "the agent that built this left receipts too". |
| 85–90 s | The URL. |

## 6. Submission copy

**Title:** *Plainly: Is this letter real? Scam check and plain-language next steps for official mail, in your language*

**Description (426 characters, fits the 512 limit):**
> Photograph an official-looking letter and get a verdict in seconds: Likely scam, Consistent with genuine, or Can't tell (never "safe"). Every red flag is quoted from the letter and checked in code against official agency contacts. Then Amazon Nova explains it in your language, computes the real deadline into a calendar file and drafts a reply. Serverless on AWS, built and deployed by Claude Code through the AWS MCP Server.

**What to emphasize:**
- Lead every surface with "is it real?", not "explains letters".
- Code decides, the model narrates.
- Receipts on both agents.
- Measured numbers only: verdict precision and recall, **false "consistent" verdicts on scam letters (target 0)**, deadline accuracy, quote-grounding rate, p50/p95 latency, measured cost per letter.
- Real tester quotes, with n.

**Impact figures (searched today; open each primary page before citing):**
- FTC: $3.5B reported lost to imposter scams in 2025, the #1 fraud category for the fifth year running. Government impersonators: about $920M (up from $789M in 2024) across more than 375K reports. [FTC press release](https://www.ftc.gov/news-events/news/press-releases/2026/06/ftc-data-show-people-reported-losing-3-point-5-billion-imposter-scams-2025) · [WBIW](https://www.wbiw.com/2026/09/28/ftc-warns-of-escalating-government-impersonation-scams-after-900-million-lost-in-2025/)
- FBI IC3 2025: more than 201,000 victims aged 60+ reported about $7.7B in losses. [IC3 2025 report](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf)
- India: about ₹22,495 crore lost to cyber fraud in 2025, and the 1930 helpline logged about 32.4M calls. These come from secondary sources; confirm against the MHA replies. [InsightsOnIndia](https://www.insightsonindia.com/2026/02/21/cybercrime-in-india/) · [MHA Rajya Sabha reply](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2026-pdfs/RS11022026/1349.pdf)
- FTC gift-card rule: consumer.ftc.gov/gift-card-scams.
- **Never invent user counts.**

**Startups path:**
- Free for consumers.
- White-label "is this real?" check for credit unions, telcos, legal aid and immigrant-services groups, at about $0.006 of cost per check.
- Roadmap: AgentCore Web Search for senders not in the registry, WhatsApp intake, voice.

## 7. Top risks and mitigations

| Risk | Mitigation |
|---|---|
| Seen as a generic document explainer | Scam verdict first in the title, the description, and the first screen. |
| A false "safe" verdict causes harm | No "safe" state. Default to "Can't tell". Always show the official number. Add a "not legal advice" notice. |
| Nova problems (model ID, structured output, low quota on a new account) | Smoke-test tonight. Model fallback chain. Sample tiles are cached. |
| Registry has wrong or stale numbers | Only ~20 agencies, each with a source URL and date checked, verified by Shrey. |
| Injection sample looks like an attempt to manipulate the AI scorer | Show the hidden text only inside the rendered image. The write-up describes it and never quotes it as an instruction. Nothing hidden anywhere on the site or in the write-up. |
| Ship gate fails during Oct 5–19 | Canary, alarms, $10 budget, no redeploys after the deadline, check daily. |
| JS-only page looks empty to the AI scorer | Pre-rendered HTML with the sample results in the page. |
| Proof screenshots rejected by moderation | Text versions in the write-up and on `/evidence`. |
| Draft left unpublished | Publish tonight, then keep editing. |
| Personal data exposure | Letters never stored, no letter text in logs, account ID masked, share feature disabled. |
| Scope creep | The cuts in section 2 are final. Nice-to-haves only after M1. |

## 8. Verdict on the existing Plainly code: keep and merge

About 60% of `C:\Users\Shrey\documents\hackathon work\zts\backend\app.py` (239 lines) can be reused.

**Keep as is:**
- Handler, routing and v2-event parsing (works behind an HTTP API).
- `respond`, `client_ip`, and the per-IP `rate_limited` with TTL.
- `build_content` with its size limits.
- The model fallback and retry loop.
- `parse_json` as the last-resort path.
- Error handling that never leaks details.
- The DynamoDB single table with `expiresAt` TTL.

**Change:**
1. `MODEL_IDS` default: make `us.amazon.nova-2-lite-v1:0` the primary. It is currently Nova Pro/Lite v1.
2. Replace the free-text JSON prompt with a forced tool call.
3. Split the pipeline into extract → verify → narrate.
4. **The model's `scam_check.risk` must no longer decide the verdict.** Move that to `verifier.py`.
5. Compute dates in Python instead of the prompt's "compute it".
6. Disable `/api/share`, or make it opt-in with a 24-hour TTL. It currently keeps result bodies for 7 days.
7. Change `print(f"ERROR ...{e}")` to structured logs without payloads.

**New code:** `verifier.py`, `registry.json`, `ics.py`, tests, the eval harness, the IaC template, and the whole frontend.

=========== REDTEAM ===========

**Red-team of the "Plainly: Is this letter real?" build brief**

These checks were run on 2026-09-30:
- I re-scanned all 150 saved submissions for scam, phish, fraud, impersonation and spoof. Only one hit came back, "spoof" in Performance Encore, and it is unrelated. The claimed gap holds for now.
- I read `backend/app.py`.
- I fetched the AWS Nova 2 Lite model card and the FTC press release.
- I checked the deadline math. It is correct: Oct 2 11:59 PM PDT is Oct 3 12:29 IST, and 23:30 IST is 11:00 AM PDT. The 426-character description count is also correct.

## Issues

**1. HIGH: "Code decides, quotes are grounded" is partly circular, and a Gate 2 judge will spot it.**
- The model writes the transcript, and the grounding check compares its quotes against that same transcript. A hallucinated transcript therefore validates a hallucinated quote.
- Threats, secrecy and "digital arrest" are also extracted by the model. That makes the model a co-decider, not only the narrator.
- Asking the model to output the full transcript also roughly doubles the output tokens, which adds latency.
- **Fix:** make Amazon Textract `DetectDocumentText` a must-have, not a nice-to-have. It costs about $0.0015 per page and takes about an hour to add.
  - Get phones, URLs, emails, amounts and dates from the Textract text with deterministic regex.
  - Ground each model quote against the Textract text, so there are two independent readers.
  - Drop the model transcript.
  - Textract does not read Devanagari. For non-Latin scripts, fall back to model-only extraction and label the result "not independently grounded".
  - Reword the claim to: "the model extracts quoted evidence; code verifies it against independent OCR and applies the rules."

**2. HIGH: The prompt-injection tile conflicts with "every flag quotes the exact line".**
- The pre-baked landing HTML, the /judges tour and the write-up would contain the hidden AI instruction as readable text. That is exactly what an AI scorer ingests.
- The scorer could be confused by it, or the entry could be flagged as attempting injection, which falls under the "misrepresentation" grounds.
- **Fix:**
  - For rule 10, never render the quoted text anywhere. Show "[instruction aimed at AI tools, redacted, visible in the image]".
  - Remove the injection tile from the landing page and the video. Keep it only on /try, as an image with neutral alt text.
  - In the write-up, describe the rule and its test count without quoting the payload.

**3. HIGH: The request will time out at 30 s on real uploads.**
- API Gateway HTTP APIs have a hard 30 s integration limit, and CloudFront's origin read timeout also defaults to 30 s.
- The plan has two sequential Bedrock calls (extract with an image, then narrate). Hindi or Spanish output is token-heavy. On top of that, the existing loop in app.py allows 2 models × 2 attempts plus a 1.5 s sleep.
- **Fix:**
  - Split into `POST /api/check` (Textract + extract + verify, returns verdict and trace) and `POST /api/explain` (narrate), called one after the other by the browser.
  - Set a hard budget per request: boto3 `read_timeout` about 12 s, one retry at most, and skip fallbacks once `context.get_remaining_time_in_millis()` is under 8 s.
  - Cap `maxTokens` and keep Nova 2 Lite reasoning off.

**4. HIGH: The per-IP rate limiter can be bypassed, and the budget alert does not stop spend.**
- `client_ip()` trusts the first `X-Forwarded-For` entry, which the client controls, so any bot can rotate that value. If the header were missing, `sourceIp` would be the CloudFront edge IP, and judges would share buckets.
- A $10 AWS Budget only sends an alert.
- **Fix:**
  - Forward `CloudFront-Viewer-Address` through the origin request policy and key the limiter on it.
  - Add a global daily cap in DynamoDB (for example 300 live analyses a day). Past the cap, serve the cached sample tiles with a friendly message.
  - Do not use a Budget action that denies Bedrock. It would kill the live demo and fail the ship gate.

**5. HIGH (ship gate / AI scorer): /evidence, /judges and /how-it-works will return 403 errors.**
- The S3 REST origin with OAC does not resolve `/path` to `/path/index.html`, so the pages the AI scorer needs would fail.
- **Fix:**
  - Add a CloudFront Function that rewrites the URI (append `index.html` when there is no extension).
  - Do not use a blanket 403→/index.html custom error response, because it would mask `/api` errors.
  - Use a cache policy with caching disabled and an `AllViewerExceptHostHeader` origin request policy, with POST allowed, on `/api/*`.
  - Check every path with `curl -A "Mozilla/5.0"` and with a bot user agent.

**6. MED-HIGH: The description overclaims.**
- "built and deployed by Claude Code through the AWS MCP Server" is not true when the deploy is `aws cloudformation deploy` from the CLI. The brief admits this itself.
- **Fix, either one:**
  - Do the production deploy through MCP: upload the template to S3, then have the agent run `CreateChangeSet` / `ExecuteChangeSet` via `call_aws`. CloudTrail then shows stack creation through `aws-mcp`, which is the strongest proof available.
  - Or reword to "built with Claude Code connected to AWS via the AWS MCP Server".
- Also attach a CloudFormation service role. Without one, stack operations use the agent's credentials, and the MCP-conditioned denies (`iam:Delete*`, `dynamodb:DeleteTable`, `s3:DeleteBucket`) could break rollbacks or replacements.
- Add a permissions boundary to the agent's `iam:*Role*` rights. Otherwise the agent can create a `plainly-*` role with admin rights (privilege escalation), and Manuela would notice.

**7. MED-HIGH: The evaluation is self-graded, so the metrics carry no weight.**
- The agent writes the rules, generates the 24 letters and labels them. A result of "0 false consistent verdicts" is guaranteed by construction.
- **Fix:**
  - Freeze the rules first.
  - Then score a hold-out set of real scam examples published by governments: FTC and IRS scam alerts, Action Fraud, PIB Fact Check posts of fake government letters, and cybercrime.gov.in advisories. US federal works are public domain; credit every source.
  - Add scam messages that testers actually received, redacted and with consent.
  - Report the synthetic and hold-out numbers separately, and publish the misses.

**8. MED: The originality framing ignores direct market competitors.**
- Norton Genie (also now inside ChatGPT, Mar 2026) and Bitdefender Scamio already accept screenshots or messages and return a scam verdict. "0 of 150 entries" is not the same as "novel", and the SA judges know these products.
- **Fix:** add a comparison table against Genie and Scamio. Plainly's differences:
  - official-agency contact registry with sources
  - quoted, OCR-grounded evidence
  - a "Can't tell" state instead of "safe"
  - real deadlines and an .ics file for genuine letters, plus a reply draft
  - multilingual output
  - no storage
- Also broaden intake to texts, emails and WhatsApp messages that claim to be from an agency. It is the same pipeline and a far larger market. Keep "official communications" as the wedge.

**9. MED: The target audience is too broad and the registry is fragile.**
- About 20 agencies across four countries (US, UK, Canada, India) is thin coverage and a trap for wrong phone numbers. Genuine agencies publish many numbers (the IRS has dozens), so rule 4 will wrongly flag genuine letters.
- Discom domains are often .com, so the "not .gov" rule fires on genuine discom letters.
- **Fix:**
  - Make one primary persona explicit: families handling official mail in a second language, India plus US.
  - Cut the registry to about 12 agencies and match on domains first, phone numbers second.
  - Decide the verdict with weighted rules: an unknown number alone should give "Can't tell", never "Likely scam".
  - Shrey verifies each entry. Budget 90 minutes, not 3 hours.

**10. MED: The Nova 2 Lite access details (checked against the AWS model card).**
- Confirmed:
  - us-east-1 has no in-Region endpoint; you must use `us.amazon.nova-2-lite-v1:0`.
  - Tool calling is supported.
  - Structured outputs are not supported.
  - Input types are text, image and video only, with no document type. The PDF "document block" path will likely fail, so go straight to pdf.js in the browser.
- The geo profile routes requests to us-east-1, us-east-2 and us-west-2. The Lambda role must allow the inference-profile ARN plus the foundation-model ARNs in all three regions. A region lock on us-east-1 anywhere (agent user, SCP, Lambda role) will cause AccessDenied errors on inference.
- Tonight, check the Service Quotas entry for Nova 2 Lite cross-region tokens per minute. New accounts can have very low defaults.
- One search summary claims Nova 2 Lite has "no tool use". That is wrong according to the AWS card, but include a working `toolChoice` in the smoke test anyway.

**11. MED: The AWS account plan and ownership are unchecked.**
- If the account is on the Free Plan, it is suspended when the credits or the 6-month term run out. That could take the app down during Gate 1 or Gate 2. Some services may also be restricted on that plan.
- **Fix:**
  - Check the plan tonight and upgrade to a paid plan if needed. Credits carry over.
  - Confirm that the AWS account, the Builder Center profile and the GitHub account are Shrey's own (satanrayshe / shrey.sati). Finalist checks compare against LinkedIn and ID, and a mismatch counts as misrepresentation.

**12. MED: The community impact evidence is weak for the Startups lane.**
- Three to five family testers and national statistics do not show a "first user base".
- **Fix:**
  - Share the live URL in two or three real groups tonight (family WhatsApp, a housing-society group, a college group).
  - Show the anonymous live counter.
  - Collect 10 to 20 named-with-consent or anonymized testers, with n stated.
  - Add one letter of interest from a legal-aid or community organization if you can get one. Otherwise say plainly that there is none yet.

**13. MED: Some cited figures are wrong or unverified.**
- The FTC release (Jun 15, 2026) confirms $3.5B lost to imposter scams in 2025 and about $920M to government impersonators. The 2024 comparison figure is **$866M, not $789M** as the brief says.
- "375K reports" and "fifth year running" did not appear in what I fetched.
- The IC3 $7.7B figure for over-60s and the India ₹22,495 crore figure are still secondary sources.
- Nova pricing comes from third parties.
- "~11 daily-life competitors" is a snapshot of 58 tagged entries out of 150. The final field will be several times larger.
- **Fix:** cite only primary pages you opened, and label the cost per letter as measured.

**14. LOW-MED: The schedule is too tight for one person.**
- By M1 there is a whole new frontend, the verifier, registry, .ics, about 30 tests, the letters, the IaC and the deploy, plus docs, a video and an eval on the last day.
- **Fix:**
  - Cut Guardrails; regex plus OCR grounding is enough.
  - Cut the language set to English and Hindi, with Spanish only if it's free.
  - Use a 60-second video.
  - Keep the canary; it is cheap insurance for the ship gate.
  - Publish the Builder Center draft tonight, as planned.

**15. LOW: Synthetic look-alikes of IRS and Treasury notices.**
- Making realistic copies of federal notices is legally touchy, and scam-looking images ("FINAL NOTICE", "arrest") may trip Builder Center image moderation, as a Kiro proof screenshot already did for another participant.
- **Fix:** put a "SAMPLE – NOT A REAL NOTICE" watermark on every image, use no seals or logos, and keep text versions of everything.

**16. LOW: Details.**
- Keep the app live through at least mid-November, not Oct 26. The eligibility checks and "next-highest" substitutions make the end date uncertain, and the cost is negligible.
- The description repeats title words, which the form guidance says not to do. Replace "scam check" with the concrete verdict states.
- Don't call the fixed pipeline "two agents", since it isn't agentic. Use "the build agent and the checker both leave receipts".
- The existing `MAX_FILE_BYTES` of 4 MB becomes about 5.3 MB after base64, close to Lambda's 6 MB limit. Enforce the 1.5 MB client downscale on the server as well.

## Verdict: GO with fixes

Do not switch. The scam-first angle is the only white space that still holds in the field (verified: 0 of 150). Payhold (C10) remains too fragile for about 60 hours of solo work.

Required fixes, in order:
1. Textract as the independent reader; drop the model transcript; regex-based entity extraction (#1).
2. Split `/api/check` and `/api/explain` with hard time budgets (#3).
3. Redact the injection text everywhere (#2).
4. Fix `client_ip` to use CloudFront-Viewer-Address and add a global daily cap with a cached fallback (#4).
5. CloudFront Function for page routes, plus the `/api` behavior policies (#5).
6. Deploy through MCP with a change set (or reword the description), add a CloudFormation service role and an IAM permissions boundary (#6).
7. Freeze the rules, then run a hold-out eval on government-published scam examples (#7).
8. Add a competitor table against Genie and Scamio, and accept screenshots of texts and emails (#8).
9. Narrow the persona and use a domain-first registry of about 12 agencies (#9).
10. Allow the Bedrock profile ARN plus all three destination regions; use pdf.js for PDFs; check the quota tonight (#10).
11. Check the account plan and ownership tonight (#11).
12. Get real testers through community groups, with n stated (#12).
13. Correct the FTC 2024 figure and cite only primary sources (#13).

Relevant files:
- `C:\Users\Shrey\documents\hackathon work\zts\backend\app.py` (issue #4 is `client_ip` at lines 84-89; the timeout-prone model loop is at lines 152-175)
- `C:\Users\Shrey\AppData\Local\Temp\claude\C--Users-Shrey-documents-hackathon-work-zts\6cf7d3ae-e3bc-4785-990e-ab8bb525c2bc\scratchpad\comp\subs.json`

Sources:
- [Nova 2 Lite model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-lite.html)
- [FTC imposter scams 2025 press release](https://www.ftc.gov/news-events/news/press-releases/2026/06/ftc-data-show-people-reported-losing-3-point-5-billion-imposter-scams-2025)
- [Norton Genie in ChatGPT](https://newsroom.gendigital.com/2026-03-04-The-Worlds-First-AI-Powered-Scam-Detector,-Norton-Genie,-Now-in-ChatGPT)
- [Bitdefender Scamio](https://www.bitdefender.com/en-us/consumer/scamio)
- [Tom's Guide comparison of AI scam detectors](https://www.tomsguide.com/computing/online-security/i-tried-3-ai-powered-scam-detectors-to-help-keep-me-safe-online-and-theres-a-clear-winner)