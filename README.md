# Plainly: Is this letter real?

Photograph an official-looking letter, text or email, or paste it in. Your phone reads it on the device, so the photo never leaves it. Plainly then tells you whether it is likely a scam, quotes the exact lines that gave it away, and gives you the official number to call instead. If the letter checks out, it explains it in English, Hindi or Spanish, works out the real deadline, gives you a calendar file and drafts a reply.

## TL;DR

- Live app: {{LIVE_URL}}
- Try it in one click: {{LIVE_URL}}/judges/ is a 90-second tour: three sample letters that open instantly, then a photo read on your own device. No sign-in.
- Video (90 seconds): {{VIDEO_URL}}
- Code: {{REPO_URL}}
- Serverless on AWS (CloudFront, S3, API Gateway, Lambda, DynamoDB, CloudWatch, SNS, Budgets), all on the AWS Free account plan. Built with Claude Code connected to the AWS account.

Plainly gives one of three verdicts:

| Verdict | Meaning |
|---|---|
| Likely scam | Strong red flags, each quoted from the letter and checked in code |
| Consistent with a genuine [agency] letter: confirm on the official number | The sender's contacts match the official registry and nothing suspicious was found |
| Can't tell | Not enough evidence either way |

There is no "safe" verdict. A letter can look perfect and still be forged, so the best Plainly will say is "consistent with genuine", followed by the agency's real phone number.

## The problem

Scammers pose as tax offices, pension agencies, police, customs and electricity companies because people are afraid of letters from them. Someone reading official mail in a second language, or an older parent, has the hardest time telling a real notice from a fake, and the hardest time acting on a real one.

- In 2025 people told the US Federal Trade Commission they lost $3.5 billion to imposter scams, about $920 million of it to government impersonators, up from $789 million in 2024. ([FTC, 15 Jun 2026](https://www.ftc.gov/news-events/news/press-releases/2026/06/ftc-data-show-people-reported-losing-3-point-5-billion-imposter-scams-2025))
- The FBI's Internet Crime Complaint Center received 201,266 complaints from people aged 60 and over in 2025, reporting $7.7 billion in losses. ([IC3 2025 Annual Report](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf))
- In India, citizens reported ₹22,845.73 crore lost to cyber fraud in 2024, up from ₹7,465.18 crore in 2023, according to the Ministry of Home Affairs. ([MHA, Lok Sabha unstarred question 432, 2 Dec 2025](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2025-pdfs/LS02122025/432.pdf))

The tools on either side of this don't join up. Letter explainers assume the letter is genuine and happily explain a fake. Scam checkers stop at "scam or not", so someone holding a real notice still doesn't know what it asks for or by when. See [docs/comparison.md](docs/comparison.md) for Norton Genie and Bitdefender Scamio.

## What I shipped

- A landing page with three sample letters side by side: a fake electricity "FINAL NOTICE", a genuine-format IRS-style notice and a "digital arrest" parcel scam. Their results are rendered into the HTML, so the page reads fine without JavaScript. Every sample is watermarked "SAMPLE — NOT A REAL NOTICE" and has no seals, logos or real personal data.
- `/try/`: take a photo, choose a PDF or screenshot, or paste the text of an SMS or email. The page reads photos and scanned PDFs on the device with Tesseract.js (English, or English plus Hindi) and uses a PDF's own text layer when it has one. The text it read appears in an editable box, so you can fix a misread word before anything is sent.
- The result: the verdict banner, every red flag with the quote it came from, a receipts panel listing each check as flag, pass or unknown, and a box that says "Do not call the number on this letter" followed by the official line and its source.
- For letters that are not a likely scam: a plain explanation, next steps, deadlines with an "Add to calendar" button, jargon explained, questions to ask and a reply draft with a copy button, in English, हिन्दी or Español. For a likely scam, the steps are don't pay and where to report it (FTC in the US, cybercrime.gov.in or 1930 in India, Report Fraud, formerly Action Fraud, in the UK).
- `/how-it-works/`, `/evidence/` (the agent-connection proof as text) and `/judges/` (a guided tour).

## Technical Innovation & Originality

Plainly's verdict comes from code you can read, and every step of it is shown to the user.

1. On-device reading. Tesseract.js and pdf.js run in the browser, self-hosted on the same CloudFront origin and loaded only when someone picks a file. The photo of a tax notice, with the reader's name, address and account numbers on it, never reaches a server. Only the text does, after the reader has seen it.
2. A rules engine on Lambda. A keyword and date reader pulls out the sender, dates, deadlines, payment demands, threats, credential requests, links and call-back numbers, each with the sentence it came from. Then 21 rules in `backend/verifier.py` score the evidence: gift cards, crypto and wire transfers, UPI payments to a personal handle, OTP and password requests, arrest and "digital arrest" threats, demanded video calls, lookalike domains (edit distance, confusable characters, punycode), shortened or raw-IP links, link bait, KYC block threats, prize and refund bait, fees before a release, "press 1" prompts, call-backs to unofficial numbers, sender impersonation, free-mail addresses posing as official, secrecy, short deadlines and unknown contacts. Strong flags are worth 3 points and medium flags 1; 3 or more is "Likely scam". "Consistent with genuine" needs a matched agency, at least one contact that matches the registry and zero points.
3. A registry of 14 agencies (5 US, 7 India, 2 UK), domains first and phones second, each entry with its source URL and the date it was checked (`backend/registry.json`, `docs/registry-sources.md`).
4. Dates are arithmetic. "Pay within 30 days of the date of this notice" becomes a date computed in Python from the quoted letter date. The explanation receives it as a fact.
5. Hidden instructions aimed at AI tools are a scam signal. A letter that tries to talk to the checker is flagged as strong evidence. The instruction itself is redacted everywhere, in the UI, the logs and this write-up, so the flag only says that one was found.
6. Receipts. Every check leaves a trace entry with its status and timing, and the page shows all of them, including the checks that passed.
7. Explanations written by people. `/api/explain` fills templates for the verdict and for each flagged rule, with actions, a glossary of official-letter terms found in the text, questions to ask and a reply draft, in English, Hindi and Spanish.

Why rules instead of a model for the verdict:

- Every "Likely scam" traces to named rules, quoted lines and a points total, and the same text always gets the same answer.
- Nothing generates reassurance. A fake that says "this is a legitimate notice", or hides instructions for AI tools, can't talk its way to a better verdict.
- A check costs Lambda time, one API request and a few DynamoDB writes, with no per-check AI charge. That keeps it free for the people it's for.
- Latency doesn't depend on a model queue or a retry chain.
- It runs on the AWS Free account plan.

The trade-off is recall, which the [Evaluation](#evaluation) section shows in numbers.

Plainly was designed around Amazon Textract as an independent reader and Amazon Nova 2 Lite for extraction and explanations, and that path is built. It is switched off because this account is on the AWS Free account plan, which includes neither service (see [Gotchas](#gotchas)). The verdict was deterministic code in that design too; the model only located quotes, and Python checked each quote against the Textract text before it could count.

None of the 150 projects in the public gallery on 30 Sep 2026 mentioned scams, phishing, fraud or impersonation (keyword scan of the gallery's public submissions API).

## Implementation Quality

- One plain CloudFormation template (`infra/template.yaml`) for the whole stack: S3 with Origin Access Control, CloudFront with a URI-rewrite function, an API Gateway HTTP API, the Lambda function, a DynamoDB table with TTL, CloudWatch alarms and dashboard, an SNS topic and a budget. The coding agent's IAM policy, a permissions boundary for any role it creates and a setup script for the owner sit next to it in `infra/`.
- One switch for the AI path. The `AiMode` parameter (default `off`) sets `AI_MODE` on the Lambda. With it off, no Bedrock or Textract client is created and the Lambda role has no Bedrock or Textract permissions.
- The Lambda has no third-party dependencies, only boto3. It runs Python 3.13 on arm64.
- Privacy: the photo stays on the device, and Plainly stores nothing about a letter. Logs are structured JSON with request ids, verdicts, rule ids and timings, and no letter text. The share feature from an earlier draft was removed because it kept results for 7 days.
- Abuse and cost controls: a per-IP limit of 20 checks an hour keyed on the `CloudFront-Viewer-Address` header that CloudFront adds (not the client-supplied `X-Forwarded-For`), a global cap of 400 checks a day, HTTP API stage throttling, a text-size limit on the server, and a secret origin header so the API can't be called around CloudFront. When a limit is hit, the page offers the sample letters.
- Tests: pytest covers the reader, every rule, the verdict, the registry, date math, routing, the template explanations in all three languages, and the AI path with Bedrock and Textract faked. `python -m pytest backend/tests -q` runs them.
- Regression tests for false positives: 25 genuine messages (bank OTP alerts, re-KYC notices, police fraud-awareness texts, a jury summons and others) that once read as scams are pinned in `backend/tests/test_false_positives.py`.
- Evaluation on real, government-published examples, scored separately from our own letters, with every miss listed. See [Evaluation](#evaluation).
- Operations, defined in the same template: a CloudWatch dashboard, alarms to email through SNS (Lambda errors, p95 duration over 20 s, API 5xx), 14-day log retention and a $10 monthly budget alert.

## Community/Market Impact

Primary users: families in India and the US who deal with official mail in a second language, and the relatives they forward it to. The person who gets the "is this real?" message on the family chat can answer it with a quote and a source instead of a guess.

- Government impersonation is a large and growing loss category in both countries (figures under [The problem](#the-problem), sources in [docs/SUBMISSION.md](docs/SUBMISSION.md)).
- India's Ministry of Home Affairs runs a national awareness campaign on "digital arrest" scams ([MHA, Rajya Sabha unstarred question 1349, 11 Feb 2026](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2026-pdfs/RS11022026/1349.pdf)) and says I4C has blocked more than 3,962 Skype IDs and 83,668 WhatsApp accounts used for them ([PIB, 25 Mar 2025](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2114750)). Plainly's rules flag the pattern directly: arrest threats, CBI or police claims and demands to stay on a video call.
- It costs nothing to use and has no sign-in. With no model in the loop, the running cost is the basic serverless services, so a free tool for individuals is realistic.
- A photo of an official letter is personal data. Reading it on the phone means people don't have to trust a server with it.

## Creativity & Storytelling

The demo opens on two letters that look alike. One is a genuine-format notice and one is a fake, and they get opposite verdicts, each backed by quoted lines and sources. A third sample, the "digital arrest" parcel scam, is the one Indian families are warned about on caller tunes and in the metro.

About two days before the deadline, the AWS account turned out to be on the Free plan, where Bedrock and Textract refuse every call. Rather than drop the entry or pay for an upgrade the owner couldn't make, the reading moved onto the phone and the explanations became written templates. The verdict didn't have to change, because it was already code. Plainly asks the same of a letter as the build asked of itself: check it before trusting it, and keep the receipts.

## How the coding agent helped me ship

| Agent did | I decided | Evidence |
|---|---|---|
| Ran a 22-agent research pass: official rules, judges, 150 competitor projects, past winners, AWS priorities | Which of 18 concepts to build, after a 4-lens weighted score | `docs/research/`, `docs/agent-log.md` |
| Red-teamed its own brief and found 16 issues | Accepted the fixes: an independent reader, split endpoints, redacted injection text, holdout eval | `docs/research/build-brief-and-redteam.md` |
| Wrote the API contract, then built backend, infra, site and docs in parallel against it | Scope cuts (no AgentCore, voice or accounts), the three-verdict design, no "safe" state | `docs/CONTRACT.md` |
| Drafted the official-contacts registry with a source URL and check date per entry | | `backend/registry.json`, `docs/registry-sources.md` |
| Tuned the rules on a dev set of 67 messages, hunted its own false positives, froze the rules by hash and ran the holdout once | Rules stay frozen after the holdout; gaps are listed, not fixed | `eval/RULES_FROZEN.md`, `eval/results.md` |
| Connected to AWS, found the Free plan, captured the exact Bedrock and Textract errors, and wrote an IAM setup script when Claude Code's permission classifier stopped it from creating IAM users itself | Not to upgrade the account; to ship Option B | `docs/agent-log.md`, `infra/setup-agent-user.sh` |
| Re-architected for the Free plan: on-device OCR, rules reader in production, template explanations in three languages, `AI_MODE` switch | "start option b" | `docs/CONTRACT.md` "Option B" |

The full timestamped log is in [docs/agent-log.md](docs/agent-log.md).

## Proof of coding agent connection to the AWS console

{{AGENT_PROOF}}

This section will hold, as text (screenshots too, with text copies in case image moderation rejects them), with the account id masked:

1. The `aws login` session the agent used and `aws sts get-caller-identity` for it.
2. The deploy of the `plainly` stack and `/api/health` answering `"ai_mode": "off"`.
3. If the AWS MCP Server is connected: the Claude Code MCP configuration and calls the agent made through it, with request ids and timestamps.
4. CloudTrail events for the agent's calls.

The same proof is mirrored on the live site at {{LIVE_URL}}/evidence/.

## Architecture on AWS

```
Phone / laptop: photo or PDF -> pdf.js text layer or Tesseract.js OCR -> editable text   (photo stays here)
      |
      v  HTTPS, text only
CloudFront -+- default -> S3 (private, OAC): pre-rendered HTML, sample results, Tesseract.js + pdf.js
            +- /api/*  -> API Gateway HTTP API -> Lambda (Python 3.13, arm64, AI_MODE=off)
                            /api/check:   rules reader -> 21 rules -> registry (14 agencies) -> date math
                            /api/explain: written templates, English / Hindi / Spanish
                            DynamoDB (rate limits, daily cap, counters; TTL)
                            CloudWatch Logs (no letter text) -> alarms -> SNS email
Also in the stack: CloudWatch dashboard, a $10 budget alert
Built and switched off: Amazon Textract, Amazon Bedrock (Nova 2 Lite)
```

The full diagram (Mermaid and ASCII), a service table with the reason for each service, and the request flow are in [docs/architecture.md](docs/architecture.md).

| Measured | Figure |
|---|---|
| Latency: on-device reading and `/api/check` | {{LATENCY}} |
| AI tokens per letter | 0 (no model call with `AI_MODE=off`) |

## Evaluation

The rules were frozen by sha256 before the holdout set was scored, and the holdout was run once. Each set is reported on its own, because the dev set was used for tuning and we wrote the synthetic letters ourselves.

These are the production engine's numbers. The live Lambda reads text with the same keyword and date reader the eval used, and applies the same frozen rules. The eval feeds letters as text, so it doesn't measure the on-device OCR step, where a misread word can change a result.

| Set | Scams → Likely scam (recall) | Precision | Scams → Consistent with genuine | Genuine → Likely scam | Genuine → Consistent with genuine |
|---|---|---|---|---|---|
| **Holdout (23), never used for tuning** | **1/12** | 1/1 | **0** | 0/11 | 8/11 |
| Dev (67), used for tuning | 25/29 | 25/25 | 0 | 0/38 | 12/38 |
| Synthetic (24), written by us | 11/12 | 11/11 | 0 | 0/12 | 12/12 |

- Holdout: 12 scam messages quoted by the FTC, IRS and FBI IC3, plus 11 genuine IRS sample notices (CP11 to CP523), transcribed with source URLs in `eval/holdout/`. Deadlines on the 5 holdout letters with a labeled deadline were all correct.
- Dev: 29 real scams from FTC, GOV.UK, PIB Fact Check and I4C; 13 published genuine IRS and DoT messages; and 25 genuine messages written from public templates to hunt false positives.
- Synthetic: 12 genuine-format and 12 scam letters from `eval/synthetic/generate.py`.

What this says: across all 114 letters, Plainly never called a scam genuine and never called a genuine letter a scam. It is cautious to a fault. On the holdout, 11 of 12 real scams came out "Can't tell", which is safe but not much help, and the high dev and synthetic recall mostly shows fit to the examples the rules were tuned on.

Known gaps, from the holdout run (details in `eval/results.md`):

- Phone-call scripts. Six of the 12 holdout scams are robocall transcripts. "Press 1." and "press 1 to get…" slip past `press_to_connect`, and offers of debt settlement, loan relief, rate reduction and rebates have no rule.
- "We will suspend your Social Security number" has no rule, although SSA says it never does this.
- Toll and late-fee texts from an unnamed service score 1 point at most. This is the most repeated miss across all sets.
- A link in a message that names no agency is judged more leniently than one that names the IRS.
- Money-waiting lures ("rebate check", "direct deposit of $1,200… accept this payment", "your unclaimed refund") don't match the lure words.
- A request for a photo of your driver's licence isn't a credential request; that rule covers secrets only.
- Two IRS phone numbers printed on genuine notices are missing from the registry, which costs those notices a point.
- The holdout has no India or UK items, and the eval has only two Hindi texts.

Reproduce: `python eval/run_eval.py --set all --out eval/results-rules-reader.md` (no AWS needed).

## Gotchas

Hit during the build, with exact error text:

- The AWS Free account plan blocks Amazon Bedrock and Amazon Textract. On a new account (`aws freetier get-account-plan-state`: `"accountPlanType": "FREE"`, $100 in credits), every Nova model tried returned `An error occurred (ValidationException) when calling the Converse operation: Operation not allowed`, and Bedrock reported `"authorizationStatus": "NOT_AUTHORIZED"` for Nova 2 Lite even though `list-inference-profiles` listed it. Textract returned `An error occurred (SubscriptionRequiredException) when calling the DetectDocumentText operation: The AWS Access Key Id needs a subscription for the service`. The owner couldn't upgrade, so we re-architected in hours. OCR moved onto the device, which also means the photo never leaves the phone. The verdict was already deterministic code. Explanations became templates written by people. The Nova and Textract path is built, passes its tests with the services faked, and is switched off by `AI_MODE`; after an upgrade, `AI_MODE=on scripts/deploy.sh` turns Nova back on for the text the device sends. Textract would also need the page to upload the photo again.
- boto3 can't use `aws login` credentials without the CRT extra. Every call failed with `MissingDependencyException` until `pip install "botocore[crt]"`.
- Claude Code's permission classifier stopped the agent from creating IAM policies and users under the root login ("Permission Grant"), and from probing services under root ("Credential Exploration"). A human decides permission grants, so the agent wrote `infra/setup-agent-user.sh` for the owner to read and run.

Designed around, from the documentation:

- Tesseract.js runs in a Web Worker with WebAssembly, so the site's Content-Security-Policy has to allow `'wasm-unsafe-eval'` and the worker, and the `.traineddata.gz` language files must be served without a `Content-Encoding: gzip` header, because Tesseract unzips them itself.
- An S3 REST origin behind Origin Access Control does not map `/judges/` style paths to `index.html`, which is why a CloudFront Function does the rewrite.
- API Gateway HTTP APIs stop waiting after 30 seconds, which is why the check and the explanation are separate requests. That mattered most for the model path.
- For the AI path: Nova 2 Lite has no in-Region endpoint in us-east-1, so calls use the `us.amazon.nova-2-lite-v1:0` inference profile and IAM must allow the profile and the model in us-east-1, us-east-2 and us-west-2. Nova 2 Lite supports tool calling but not structured outputs, so extraction is a forced tool call.

## Limitations

- The rules reader matches patterns. It doesn't understand a letter, so scams phrased in ways it doesn't know come out "Can't tell" (1 of 12 holdout scams caught).
- On-device OCR can misread a blurry or skewed photo. The editable text box is there for that, and pasting the text always works.
- The registry covers 14 agencies: 5 in the US, 7 in India and 2 in the UK. For a sender outside it, Plainly can still flag a scam, but the best it can say about a clean letter is "Can't tell".
- Real agencies publish many phone numbers. A genuine number missing from the registry lowers confidence but never produces "Likely scam" on its own.
- Plainly does not visit links or check domain reputation. It compares domains against the registry and looks for lookalikes.
- Explanations come in English, Hindi and Spanish. Any other language falls back to English.
- Hindi letters are read on the device, but the eval has only two Hindi texts, so Hindi accuracy is unmeasured.
- The evaluation set is small. Treat the numbers as a first measurement.
- Plainly is not legal advice. When it says "consistent with genuine", it still tells you to confirm on the official number.

## Where it's headed (Startups)

- Free for individuals. With no model in the loop, a check costs basic serverless usage.
- The paid product would be a white-label "is this real?" check for organisations that already get these calls every day: credit unions and banks, telcos, legal-aid clinics and immigrant-services groups. Each would get its own branding and registry, with the check embedded in its own help channel.
- With a Paid-plan account, `AI_MODE=on` hands the reading of the text to Nova (and to Textract, if the page uploads the photo again), which may catch phrasing the keyword reader misses. Their quotes are still checked in code before they count, and the rules still decide.
- Next features: rules for the holdout gaps (with a fresh holdout to measure them), senders that are not in the registry, intake through WhatsApp where the messages already arrive, voice for people who would rather listen, and more agencies and languages with each entry sourced and dated.

## Category & lane

- Category: #daily-life-enhancement
- Lane: #startups
- Other tags: #aws-lambda, #serverless, #security

## Repository layout

```
backend/    Lambda: app.py (routing), pipeline.py, reader.py, verifier.py, lexicon.py, contacts.py, agencies.py,
            dates.py, explain_templates.py, registry.json, bedrock.py (AI_MODE=on only), tests/
infra/      template.yaml (CloudFormation), cf-function.js, agent IAM policies, setup-agent-user.sh
scripts/    deploy.sh, package_lambda.py, build_site.py, dev_server.py, render_letters.py, render_art.py,
            run_samples.py, smoke_bedrock.py (AI_MODE=on only)
site/       static HTML/CSS/JS, no framework; vendor/ holds pdf.js and Tesseract.js
samples/    synthetic showcase letters (watermarked) and their results
eval/       dev, holdout and synthetic sets, run_eval.py, results.md
docs/       CONTRACT.md, RUNBOOK.md, architecture.md, comparison.md, agent-log.md, SUBMISSION.md, cover.png
```

## Running it

Tests (no AWS needed):

```bash
python -m pip install pytest
python -m pytest backend/tests -q
```

Run the whole app locally, the same way it runs on Lambda:

```bash
python scripts/run_samples.py          # sample results -> samples/results/
python scripts/build_site.py
python scripts/dev_server.py           # http://127.0.0.1:8000
python eval/run_eval.py --set all --out eval/results-rules-reader.md
```

Deploy (needs an AWS profile with rights to the stack; Git Bash works on Windows). The full order of steps is in [docs/RUNBOOK.md](docs/RUNBOOK.md):

```bash
AI_MODE=off ALERT_EMAIL=you@example.com bash scripts/deploy.sh
```

## License

MIT. See [LICENSE](LICENSE). Tesseract.js, its language data and pdf.js are Apache-2.0; their licenses are in `site/vendor/`.
