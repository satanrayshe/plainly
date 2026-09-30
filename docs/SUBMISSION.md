# Builder Center submission draft

Paste the fields below into the project form on the hackathon's "Your project" tab. Publishing is submitting: publish early, then keep editing until Oct 2, 11:59 PM PDT.

Fill every `{{...}}` placeholder before the final publish. The list is at the bottom of this file.

## Form fields

Title (29 of 255 characters):

```
Plainly: Is this letter real?
```

Description (505 of 512 characters, counted with Python `len()`; shares no words with the title, as the form guidance asks):

```
Photograph an official-looking notice, text or email and get one of three verdicts: Likely scam, Consistent with a genuine agency notice (confirm on the official number), or Can't tell. Never "safe". Each red flag quotes the exact line, checked in code against independent OCR and a sourced registry of agency contacts. Amazon Nova then explains it in your language, turns deadlines into calendar files and drafts a reply. Serverless on AWS, built with Claude Code connected to AWS via the AWS MCP Server.
```

Tags (five maximum; the first two are required):

```
#daily-life-enhancement
#startups
#amazon-bedrock
#aws-lambda
#security
```

The lane tag is `#startups`, plural, as confirmed by the organiser. Check on the form that `#amazon-bedrock`, `#aws-lambda` and `#security` exist in exactly this spelling before publishing.

Links:

- Endpoint or live demo: {{LIVE_URL}}
- GitHub repository: {{REPO_URL}} (public, on the satanrayshe account)
- Notebook: leave empty

Cover image: 1200x675, no text in the image, under 2 MB: `docs/cover.png` (source `docs/art/cover.html`, rendered by `python scripts/render_art.py`).

## Body

Paste everything from here down to the "Placeholders to fill" heading into the body field.

### TL;DR

- Live app: {{LIVE_URL}}
- Try it in one click: {{LIVE_URL}}/judges/ walks through three sample letters in about a minute, with no upload and no sign-in.
- Video (90 seconds): {{VIDEO_URL}}
- Code: {{REPO_URL}}
- Built with Claude Code connected to AWS via the AWS MCP Server (Agent Toolkit for AWS).

Plainly gives one of three verdicts:

| Verdict | Meaning |
|---|---|
| Likely scam | Strong red flags, each quoted from the letter and checked in code |
| Consistent with a genuine [agency] letter: confirm on the official number | The sender's contacts match the official registry and nothing suspicious was found |
| Can't tell | Not enough evidence either way |

There is no "safe" verdict. A letter can look perfect and still be forged, so the best Plainly will say is "consistent with genuine", followed by the agency's real phone number.

### The problem

Scammers pose as tax offices, pension agencies, police, customs and electricity companies because people are afraid of letters from them. Someone reading official mail in a second language, or an older parent, has the hardest time telling a real notice from a fake, and the hardest time acting on a real one.

- In 2025 people told the US Federal Trade Commission they lost $3.5 billion to imposter scams, about $920 million of it to government impersonators, up from $789 million in 2024. ([FTC, 15 Jun 2026](https://www.ftc.gov/news-events/news/press-releases/2026/06/ftc-data-show-people-reported-losing-3-point-5-billion-imposter-scams-2025))
- The FBI's Internet Crime Complaint Center received 201,266 complaints from people aged 60 and over in 2025, reporting $7.7 billion in losses. ([IC3 2025 Annual Report](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf))
- In India, citizens reported ₹22,845.73 crore lost to cyber fraud in 2024, up from ₹7,465.18 crore in 2023, according to the Ministry of Home Affairs. ([MHA, Lok Sabha unstarred question 432, 2 Dec 2025](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2025-pdfs/LS02122025/432.pdf))

The tools on either side of this don't join up. Letter explainers assume the letter is genuine and happily explain a fake. Scam checkers stop at "scam or not", so someone holding a real notice still doesn't know what it asks for or by when. See [docs/comparison.md]({{REPO_URL}}/blob/main/docs/comparison.md) for Norton Genie and Bitdefender Scamio.

### What I shipped

- A landing page with three sample letters side by side: a fake electricity "FINAL NOTICE", a genuine-format IRS-style notice and a "digital arrest" parcel scam. Their results are rendered into the HTML, so the page reads fine without JavaScript. Every sample is watermarked "SAMPLE — NOT A REAL NOTICE" and has no seals, logos or real personal data.
- `/try/`: upload a photo, PDF or screenshot (camera capture works on phones), or paste the text of an SMS or email. Choose English, Hindi, Spanish or type another language.
- The result: the verdict banner, every red flag with the quote it came from, a receipts panel listing each check as flag, pass or unknown, and a box that says "Do not call the number on this letter" followed by the official line and its source.
- For letters that are not a likely scam: a plain explanation, next steps, deadlines with an "Add to calendar" button, jargon explained, questions to ask and a reply draft with a copy button. For a likely scam, the steps are don't pay and where to report it (FTC in the US, cybercrime.gov.in or 1930 in India, Report Fraud, formerly Action Fraud, in the UK).
- `/how-it-works/`, `/evidence/` (the agent-connection proof as text) and `/judges/` (a guided tour).

### Technical Innovation & Originality

The model reads the letter and explains it; code makes the decision.

1. Two independent readers. Amazon Textract reads the image. Separately, Amazon Nova 2 Lite extracts claims (sender, dates, payment demands, threats) through a forced tool call, and has to give the exact quote for each one. Python then checks every quote against the Textract text, after normalising case, whitespace and punctuation, with a fuzzy match at 0.85 or above as the fallback. A strong flag whose quote is not in the OCR text is downgraded to medium and marked "not grounded", so a quote the model made up can never count as strong evidence.
2. Deterministic verdict. Thirteen rules in `backend/verifier.py` score the evidence: gift cards, crypto and wire transfers, UPI payments to a personal handle, requests for an OTP or password, arrest threats, demanded video calls, lookalike domains (edit distance, confusable characters, punycode), free-mail addresses posing as official, secrecy, deadlines under 72 hours and contacts missing from the registry. A score of 3 or more is "Likely scam". "Consistent with genuine" needs a matched agency, at least one contact that matches the registry, a score of zero and grounded quotes. Everything else is "Can't tell".
3. Phones, URLs and email addresses come from regular expressions run on the OCR text. The model's lists are merged only when they are grounded.
4. Dates are arithmetic. "Pay within 30 days of the date of this notice" becomes a date computed in Python from the quoted letter date, and the explanation step receives it as a fact. The model never does date math.
5. Hidden instructions aimed at AI tools are a scam signal. A letter that tries to talk to the checker is flagged as strong evidence. The instruction itself is redacted everywhere, in the UI, the logs and this write-up, so the flag only says that one was found.
6. Receipts. Every check leaves a trace entry with its status and timing, and the page shows all of them, including the checks that passed.

None of the 150 projects in the public gallery on 30 Sep 2026 mentioned scams, phishing, fraud or impersonation (keyword scan of the gallery's public submissions API).

### Implementation Quality

- One plain CloudFormation template (`infra/template.yaml`) for the whole stack: S3 with Origin Access Control, CloudFront with a URI-rewrite function, an API Gateway HTTP API, the Lambda function and a DynamoDB table with TTL. The coding agent's IAM policy and a permissions boundary for any role it creates sit next to it in `infra/`.
- The Lambda has no third-party dependencies, only boto3. It runs Python 3.13 on arm64.
- Plainly stores nothing about a letter. (Amazon Textract may keep inputs to improve the service unless the account opts out through an AWS Organizations AI services opt-out policy; the runbook sets that up before launch.) Logs are structured JSON with request ids, verdicts, rule ids, timings and token counts, and no letter text. The share feature from an earlier draft was removed because it kept results for 7 days.
- Abuse and cost controls: a per-IP limit of 20 checks an hour keyed on the `CloudFront-Viewer-Address` header that CloudFront adds (not the client-supplied `X-Forwarded-For`), a global cap of 400 checks a day, HTTP API stage throttling and a payload limit enforced on the server. When a limit is hit, the page offers the sample letters.
- Time budgets: the check and the explanation are separate requests, so neither gets near API Gateway's 30-second limit. The extract call has a 14-second read timeout and at most one retry, and model fallbacks are skipped when less than 8 seconds remain.
- Model fallback chain: Nova 2 Lite, then Nova Pro, then Nova Lite. If a forced tool choice is rejected, the code retries with `any`, then parses JSON from text.
- Tests: pytest covers the verifier rules, quote grounding, date math and routing, with Bedrock and Textract mocked: 285 tests, all passing.
- Evaluation on real, government-published scam examples, scored separately from synthetic letters, with the misses listed. See the Evaluation section below.
- Operations, defined in the same template: a CloudWatch dashboard, four alarms to email through SNS (Lambda errors, p95 duration over 20 s, API 5xx, Bedrock throttles), 14-day log retention and a $10 monthly budget alert. {{CONFIRM: synthetic canary}}

### Community/Market Impact

Primary users: families in India and the US who deal with official mail in a second language, and the relatives they forward it to. The person who gets the "is this real?" message on the family chat can answer it with a quote and a source instead of a guess.

- Government impersonation is a large and growing loss category in both countries (figures under The problem, sources at the end of this write-up).
- India's Ministry of Home Affairs runs a national awareness campaign on "digital arrest" scams ([MHA, Rajya Sabha unstarred question 1349, 11 Feb 2026](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2026-pdfs/RS11022026/1349.pdf)) and says I4C has blocked more than 3,962 Skype IDs and 83,668 WhatsApp accounts used for them ([PIB, 25 Mar 2025](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2114750)). Plainly's rules flag the pattern directly: arrest threats, CBI or police claims and demands to stay on a video call.
- Cost per letter, measured from Bedrock usage fields and AWS pricing: {{COST_PER_LETTER}}.
- People who have tried it: {{TESTERS}} (n stated, quotes with consent).

### Creativity & Storytelling

The demo opens on two letters that look alike. One is a genuine-format notice and one is a fake, and they get opposite verdicts, each backed by quoted lines and sources. A third sample, the "digital arrest" parcel scam, is the one Indian families are warned about on caller tunes and in the metro.

The build follows the same idea as the product. The coding agent that built Plainly was connected to AWS through the AWS MCP Server {{CONFIRM: with its own IAM identity and a policy that denies deletes and switching off the audit log}}, and CloudTrail recorded its MCP calls. Plainly asks the same of a letter: check it before trusting it, and keep the receipts.

### How the coding agent helped me ship

| Agent did | I decided | Evidence |
|---|---|---|
| Ran a 22-agent research pass: official rules, judges, 150 competitor projects, past winners, AWS priorities | Which of 18 concepts to build, after a 4-lens weighted score | `docs/research/`, `docs/agent-log.md` |
| Red-teamed its own brief and found 16 issues | Accepted the fixes: Textract as an independent reader, split endpoints, redacted injection text, holdout eval | `docs/research/build-brief-and-redteam.md` |
| Wrote the API contract, then built backend, infra, site and docs in parallel against it | Scope cuts (no AgentCore, voice or accounts), the three-verdict design, no "safe" state | `docs/CONTRACT.md` |
| Drafted the official-contacts registry with a source URL per entry | Checked every number and domain against its source | `backend/registry.json` {{CONFIRM}} |
| {{AGENT_ROWS_AFTER_DEPLOY}} | | |

The full timestamped log is in [docs/agent-log.md]({{REPO_URL}}/blob/main/docs/agent-log.md).

### Proof of coding agent connection to the AWS console

{{AGENT_PROOF}}

This section will hold, as text (screenshots too, with text copies in case image moderation rejects them):

1. The Claude Code MCP configuration for the AWS MCP Server (`https://aws-mcp.us-east-1.api.aws/mcp`).
2. The output of `aws configure agent-toolkit` for the dedicated agent profile.
3. `aws sts get-caller-identity` for that profile, with the account id masked.
4. Calls the agent made through MCP on the deployed Lambda and CloudFront distribution, with request ids and timestamps.
5. A CloudWatch Logs Insights query over the CloudTrail trail filtered on `eventSource = "aws-mcp.amazonaws.com"`.

Claude Code was connected to AWS via the AWS MCP Server. {{CONFIRM: say which resources were created or changed through MCP calls and which through `scripts/deploy.sh` from the agent's shell (CLI calls).}}

The same proof is mirrored on the live site at {{LIVE_URL}}/evidence/.

### Architecture on AWS

```
Browser -> CloudFront -+- default -> S3 (private, OAC): pre-rendered HTML + sample results
                       +- /api/*  -> API Gateway HTTP API -> Lambda (Python 3.13, arm64)
                                       /api/check:   Textract OCR -> Bedrock extract -> Python verify
                                       /api/explain: Bedrock narrate in the chosen language
                                       DynamoDB (rate limits, daily cap, counters; TTL)
                                       CloudWatch Logs (no letter text)
Also in the stack: SNS alerts, CloudWatch alarms and dashboard, a $10 budget alert
Account level: CloudTrail trail with AWS MCP data events
```

The full diagram (Mermaid and ASCII), a service table with the reason for each service, and the request flow are in [docs/architecture.md]({{REPO_URL}}/blob/main/docs/architecture.md).

| Per letter | Figure |
|---|---|
| Bedrock tokens (check + explain) | {{TOKENS_PER_LETTER}} |
| Cost, all services | {{COST_PER_LETTER}} |
| Latency p50 / p95, `/api/check` | {{LATENCY_CHECK}} |
| Latency p50 / p95, `/api/explain` | {{LATENCY_EXPLAIN}} |

### Evaluation

The rules were frozen before the holdout set was scored. Synthetic letters and real examples are reported separately, because the agent wrote the synthetic ones and they would flatter the rules.

- Holdout: 12 scam messages quoted by the FTC, IRS and FBI IC3, plus 11 genuine IRS sample notices (CP11 to CP523), transcribed with their source URLs and labels in `eval/holdout/`. There are no India or UK items yet: the PIB, TRAI, MHA and HMRC pages we could fetch show scam messages only as images or paraphrase them.
- Synthetic: generated labeled letters in `eval/synthetic/`.
- Metrics: verdict precision and recall, false "consistent with genuine" verdicts on scam letters (the number that matters most; target 0), deadline accuracy and quote-grounding rate.

Live numbers are pending. They will come from a run against Amazon Nova on Bedrock once AWS is connected, and the table will go here. `eval/results.md` currently holds an offline dry run on the frozen rules, in which a keyword stand-in replaced the model. It checks the rules and wiring and is not the published result.

{{EVAL_TABLE}}

Misses are listed in `eval/results.md`. Reproduce with `python eval/run_eval.py --live` (needs AWS credentials).

### Gotchas

From the AWS documentation, checked while planning:

- Nova 2 Lite has no in-Region endpoint in us-east-1. Use the geo inference profile `us.amazon.nova-2-lite-v1:0`, and allow it plus the foundation model in us-east-1, us-east-2 and us-west-2 in IAM, because the profile routes to all three.
- Nova 2 Lite supports tool calling but not structured outputs, so structured extraction has to go through a forced tool call.
- Textract text detection supports English, Spanish, German, Italian, French and Portuguese. A letter in Devanagari cannot be grounded independently.
- An S3 REST origin behind Origin Access Control does not map `/judges/` style paths to `index.html`, which is why a CloudFront Function does the rewrite.
- API Gateway HTTP APIs stop waiting after 30 seconds, which is why the check and the explanation are separate requests.

Hit during the build, with exact error text:

{{GOTCHAS_HIT}}

### Limitations

- The registry covers 14 agencies: 5 in the US, 7 in India and 2 in the UK. For a sender outside it, Plainly can still flag a scam, but the best it can say about a clean letter is "Can't tell".
- Letters in Hindi or other scripts Textract does not read are checked on the model's reading alone, and the result says the quotes were not independently grounded.
- Real agencies publish many phone numbers. A genuine number missing from the registry lowers confidence but never produces "Likely scam" on its own.
- Plainly does not visit links or check domain reputation. It compares domains against the registry and looks for lookalikes.
- The evaluation set is small. Treat the numbers as a first measurement.
- Plainly is not legal advice. When it says "consistent with genuine", it still tells you to confirm on the official number.

### Where it's headed (Startups)

- Free for individuals. The per-letter cost ({{COST_PER_LETTER}}) makes that affordable.
- The paid product would be a white-label "is this real?" check for organisations that already get these calls every day: credit unions and banks, telcos, legal-aid clinics and immigrant-services groups. Each would get its own branding and registry, with the check embedded in its own help channel.
- Next features: looking up senders that are not in the registry, intake through WhatsApp where the messages already arrive, voice for people who would rather listen, and more agencies and languages with each entry sourced and dated.

### Category & lane

- Category: #daily-life-enhancement
- Lane: #startups
- Other tags: #amazon-bedrock, #aws-lambda, #security

### Sources for the figures

Every figure above was read on the primary page on 30 Sep 2026. Secondary reports were used only to find these pages.

| Figure | Source |
|---|---|
| $3.5 billion reported lost to imposter scams in 2025; imposter scams were reported more than any other fraud category, nearly one in three fraud reports | FTC press release, 15 Jun 2026: https://www.ftc.gov/news-events/news/press-releases/2026/06/ftc-data-show-people-reported-losing-3-point-5-billion-imposter-scams-2025 |
| About $920 million lost to government impersonators in 2025, up from $789 million in 2024 (business impersonators: nearly $1 billion, up from $866 million) | Same FTC release |
| Total fraud losses reported to the FTC in 2025: about $16 billion, the highest on record | Same FTC release |
| People aged 60+: 201,266 complaints and $7.7 billion in reported losses in 2025 (37% more complaints and 59% more losses than 2024) | FBI IC3 2025 Annual Report, elder fraud section: https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf |
| Government impersonation, all ages: 32,424 complaints and $797,943,193 in losses in 2025 | Same IC3 report, crime-type tables |
| India: amount reported lost to cyber fraud ₹2,290.24 crore (2022), ₹7,465.18 crore (2023), ₹22,845.73 crore (2024); 22,68,346 incidents on the National Cyber Crime Reporting Portal in 2024 | MHA, Lok Sabha unstarred question 432, 2 Dec 2025: https://www.mha.gov.in/MHA1/Par2017/pdfs/par2025-pdfs/LS02122025/432.pdf |
| India, 2021 to 2025: more than 65,89,201 financial fraud complaints on the portal, more than ₹55,050 crore reported | MHA, Lok Sabha unstarred question 251, 21 Jul 2026: https://www.mha.gov.in/MHA1/Par2017/pdfs/par2026-pdfs/LS21072026/251.pdf |
| National awareness campaign on "digital arrest" scams; helpline 1930 and cybercrime.gov.in for reporting | MHA, Rajya Sabha unstarred question 1349, 11 Feb 2026: https://www.mha.gov.in/MHA1/Par2017/pdfs/par2026-pdfs/RS11022026/1349.pdf |
| I4C blocked more than 3,962 Skype IDs and 83,668 WhatsApp accounts used for "digital arrest" | PIB (Ministry of Home Affairs), "Incidents of Digital Arrest", 25 Mar 2025: https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2114750 |
| "Gift cards are for gifts. Only gifts. Not for payments." | FTC consumer advice, "Avoiding and Reporting Gift Card Scams": https://consumer.ftc.gov/articles/avoiding-and-reporting-gift-card-scams |

## Placeholders to fill

Not part of the body.

| Placeholder | Fill with | Where it comes from |
|---|---|---|
| `{{LIVE_URL}}` | CloudFront URL, `https://...cloudfront.net` | Stack output after deploy |
| `{{REPO_URL}}` | `https://github.com/satanrayshe/<repo>` | After the repo is made public |
| `{{VIDEO_URL}}` | `{{LIVE_URL}}/demo.mp4` and the upload link | After recording |
| `{{AGENT_PROOF}}` | The five text blocks listed in that section | After the MCP connection and deploy |
| `{{AGENT_ROWS_AFTER_DEPLOY}}` | More rows for the agent table, each with an evidence path | `docs/agent-log.md` |
| `{{EVAL_TABLE}}`, `{{EVAL_SUMMARY}}` | Holdout and synthetic results, separate, misses listed | `eval/results.md` |
| `{{COST_PER_LETTER}}`, `{{TOKENS_PER_LETTER}}` | Measured from Converse `usage` fields and Bedrock and Textract pricing | `samples/results/*.json` meta, AWS pricing pages |
| `{{LATENCY_CHECK}}`, `{{LATENCY_EXPLAIN}}` | p50 and p95 in seconds | Eval run or CloudWatch |
| `{{TESTERS}}` | Tester count (n) and quotes with consent. If there are none, say so. | Real people only |
| `{{GOTCHAS_HIT}}` | Exact error text from the smoke tests and deploy | Terminal output, `docs/agent-log.md` |
| `{{CONFIRM: ...}}` | Keep the sentence only if it turned out true, otherwise delete it | The deployed stack |

Rules for filling them: no invented numbers, no user counts beyond real testers, no letter content from real people, and never quote the hidden AI instruction from the injection sample.

## Notes for the final pass

- The research brief gave the 2024 government-impersonator figure as $789 million, and the red-team said it should be $866 million. The FTC release says $789 million for government impersonators and $866 million for business impersonators, so $789 million is right.
- The IC3 elder figures above come from the PDF itself (elder fraud section, and the age-group chart description on the 2025 complaints page).
- The India figure of ₹22,495 crore for 2025 in the research notes came from a secondary site and does not appear in the MHA replies checked here, so it is not used.
- Keep README.md and this file in sync. The body above was generated from README.md with headings moved down one level and repo links made absolute.
