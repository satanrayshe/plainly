# Builder Center submission draft

Paste the fields below into the project form on the hackathon's "Your project" tab. Publishing is submitting: publish early, then keep editing until Oct 2, 11:59 PM PDT.

## Form fields

Title (47 of 255 characters):

```
Plainly: Is this letter real? Receipts included
```

Description (510 of 512 characters, counted with Python `len()`; shares no words with the title, as the form guidance asks):

```
Photograph an official-looking notice, SMS or email. Your phone reads it on the device with Tesseract, so the photo never leaves it. On AWS Lambda, 21 deterministic rules and a sourced registry of 14 agencies give one of three verdicts: Likely scam, Consistent with a genuine notice (confirm on the official number), or Can't tell. Never "safe". Each red flag quotes the exact words. Deadlines become calendar files; explanations come in English, Hindi or Spanish. Free-plan serverless, built with Claude Code.
```

Tags (five maximum; the first two are required):

```
#daily-life-enhancement
#startups
#aws-lambda
#serverless
#security
```

- `#daily-life-enhancement` is the category and `#startups` (plural, as confirmed by the organiser) the lane.
- `#aws-lambda`: the whole engine runs in one Lambda function.
- `#serverless`: every piece of the stack is serverless (API Gateway HTTP API, Lambda, DynamoDB on-demand; CloudFront and S3 are in the template, off until AWS verifies the account).
- `#security`: it is a scam and impersonation checker.
- `#amazon-bedrock` was dropped because Bedrock doesn't run in the live product. Check on the form that `#aws-lambda`, `#serverless` and `#security` exist in exactly this spelling before publishing.

Links:

- Endpoint or live demo: https://3nf75pgrv4.execute-api.us-east-1.amazonaws.com
- GitHub repository: https://github.com/satanrayshe/plainly (public, on the satanrayshe account)
- Notebook: leave empty

Cover image: 1200x675, no text in the image, under 2 MB: `docs/cover.png` (source `docs/art/cover.html`, rendered by `python scripts/render_art.py`).

## How the write-up maps to the judging criteria

| Criterion (25% each) | Where the write-up answers it |
|---|---|
| Technical Innovation & Originality | On-device OCR so the photo never leaves the phone; 21 deterministic rules with quoted evidence and a receipts trace; a sourced registry of 14 agencies; date math in code; hidden AI instructions treated as a scam signal; why rules are the right design for a verdict; the AI path built and switched off by one parameter |
| Implementation Quality | One CloudFormation template; `AiMode` switch with no Bedrock or Textract permissions when off; boto3-only Lambda; rate limits and daily cap (origin secret once CloudFront is on); tests including false-positive regressions; frozen-rules eval with a holdout run once; alarms, dashboard and budget |
| Community/Market Impact | Families handling official mail in a second language (India and US); cited loss figures; "digital arrest" pattern flagged directly; free to use because no per-check AI cost; privacy of letter photos |
| Creativity & Storytelling | Look-alike genuine and fake samples with opposite verdicts; the Free-plan twist and the re-architecture that followed; "keep the receipts" as the thread through product and build |
| Ship gate (pass/fail): documented proof of coding agent connection to the AWS console | "How the coding agent helped me ship", "Proof of coding agent connection" (text: `aws login`, MCP config and calls, the guardrail AccessDenied, CloudTrail events), `docs/agent-log.md` |

## Body

Paste everything from here down to the "Notes for the final pass" heading into the body field.

### TL;DR

- Live app: https://3nf75pgrv4.execute-api.us-east-1.amazonaws.com
- Try it in one click: https://3nf75pgrv4.execute-api.us-east-1.amazonaws.com/judges/ is a 90-second tour: three sample letters that open instantly, then a photo read on your own device. No sign-in.
- Code: https://github.com/satanrayshe/plainly
- Serverless on AWS (API Gateway, Lambda, DynamoDB, CloudWatch, SNS, Budgets), all on the AWS Free account plan. One Lambda serves both the site and the API, because AWS hasn't yet verified this new account for CloudFront; CloudFront and S3 are ready in the template behind one switch. Built with Claude Code connected to the AWS account.

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

The tools on either side of this don't join up. Letter explainers assume the letter is genuine and happily explain a fake. Scam checkers stop at "scam or not", so someone holding a real notice still doesn't know what it asks for or by when. See [docs/comparison.md](https://github.com/satanrayshe/plainly/blob/main/docs/comparison.md) for Norton Genie and Bitdefender Scamio.

### What I shipped

- A landing page with three sample letters side by side: a fake electricity "FINAL NOTICE", a genuine-format IRS-style notice and a "digital arrest" parcel scam. Their results are rendered into the HTML, so the page reads fine without JavaScript. Every sample is watermarked "SAMPLE — NOT A REAL NOTICE" and has no seals, logos or real personal data.
- `/try/`: take a photo, choose a PDF or screenshot, or paste the text of an SMS or email. The page reads photos and scanned PDFs on the device with Tesseract.js (English, or English plus Hindi) and uses a PDF's own text layer when it has one. The text it read appears in an editable box, so you can fix a misread word before anything is sent.
- The result: the verdict banner, every red flag with the quote it came from, a receipts panel listing each check as flag, pass or unknown, and a box that says "Do not call the number on this letter" followed by the official line and its source.
- For letters that are not a likely scam: a plain explanation, next steps, deadlines with an "Add to calendar" button, jargon explained, questions to ask and a reply draft with a copy button, in English, हिन्दी or Español. For a likely scam, the steps are don't pay and where to report it (FTC in the US, cybercrime.gov.in or 1930 in India, Report Fraud, formerly Action Fraud, in the UK).
- `/how-it-works/`, `/evidence/` (the agent-connection proof as text) and `/judges/` (a guided tour).

### Technical Innovation & Originality

Plainly's verdict comes from code you can read, and every step of it is shown to the user.

1. On-device reading. Tesseract.js and pdf.js run in the browser, self-hosted on the site's own origin and loaded only when someone picks a file. The photo of a tax notice, with the reader's name, address and account numbers on it, never reaches a server. Only the text does, after the reader has seen it.
2. A rules engine on Lambda. A keyword and date reader pulls out the sender, dates, deadlines, payment demands, threats, credential requests, links and call-back numbers, each with the sentence it came from. Then 21 rules in `backend/verifier.py` score the evidence: gift cards, crypto and wire transfers, UPI payments to a personal handle, OTP and password requests, arrest and "digital arrest" threats, demanded video calls, lookalike domains (edit distance, confusable characters, punycode), shortened or raw-IP links, link bait, KYC block threats, prize and refund bait, fees before a release, "press 1" prompts, call-backs to unofficial numbers, sender impersonation, free-mail addresses posing as official, secrecy, short deadlines and unknown contacts. Strong flags are worth 3 points and medium flags 1; 3 or more is "Likely scam". "Consistent with genuine" needs a matched agency, at least one contact that matches the registry and zero points.
3. A registry of 14 agencies (5 US, 7 India, 2 UK), domains first and phones second, each entry with its source URL and the date it was checked (`backend/registry.json`, `docs/registry-sources.md`).
4. Dates are arithmetic. "Pay within 30 days of the date of this notice" becomes a date computed in Python from the quoted letter date. The explanation receives it as a fact.
5. Hidden instructions aimed at AI tools are a scam signal. A letter that tries to talk to the checker is flagged as strong evidence. The instruction itself is redacted everywhere, in the UI, the logs and this write-up, so the flag only says that one was found.
6. Receipts. Every check leaves a trace entry with its status and timing, and the page shows all of them, including the checks that passed.
7. Pre-written explanations. `/api/explain` fills fixed templates (nothing is generated per letter; the text was drafted with the coding agent, and the Hindi and Spanish still need a native-speaker review) for the verdict and for each flagged rule, with actions, a glossary of official-letter terms found in the text, questions to ask and a reply draft, in English, Hindi and Spanish.

Why rules instead of a model for the verdict:

- Every "Likely scam" traces to named rules, quoted lines and a points total, and the same text always gets the same answer.
- Nothing generates reassurance. A fake that says "this is a legitimate notice", or hides instructions for AI tools, can't talk its way to a better verdict.
- A check costs Lambda time, one API request and a few DynamoDB writes, with no per-check AI charge. That keeps it free for the people it's for.
- Latency doesn't depend on a model queue or a retry chain.
- It runs on the AWS Free account plan.

The trade-off is recall, which the Evaluation section below shows in numbers.

Plainly was designed around Amazon Textract as an independent reader and Amazon Nova 2 Lite for extraction and explanations, and that path is built. It is switched off because this account is on the AWS Free account plan, which includes neither service (see Gotchas below). The verdict was deterministic code in that design too; the model only located quotes, and Python checked each quote against the Textract text before it could count.

None of the 150 projects in the public gallery on 30 Sep 2026 mentioned scams, phishing, fraud or impersonation (keyword scan of the gallery's public submissions API).

### Implementation Quality

- One plain CloudFormation template (`infra/template.yaml`) for the whole stack: an API Gateway HTTP API, the Lambda function, a DynamoDB table with TTL, CloudWatch alarms and dashboard, an SNS topic and a budget. A `UseCloudFront` parameter adds a private S3 bucket with Origin Access Control and CloudFront with a URI-rewrite function. It is `false` on the live stack because CloudFront refused this new, unverified account, so the Lambda serves the site itself (`backend/static_site.py`: the same CSP and security headers CloudFront would add, clean URLs, gzip). The coding agent's IAM policy, a permissions boundary for any role it creates and a setup script for the owner sit next to it in `infra/`.
- One switch for the AI path. The `AiMode` parameter (default `off`) sets `AI_MODE` on the Lambda. With it off, no Bedrock or Textract client is created and the Lambda role has no Bedrock or Textract permissions.
- The Lambda has no third-party dependencies, only boto3. It runs Python 3.13 on arm64.
- Privacy: the photo stays on the device, and Plainly stores nothing about a letter. Logs are structured JSON with request ids, verdicts, rule ids and timings, and no letter text. The share feature from an earlier draft was removed because it kept results for 7 days.
- Abuse and cost controls: a per-IP limit of 20 checks an hour (never keyed on the client-supplied `X-Forwarded-For`), a global cap of 400 checks a day, HTTP API stage throttling (5 requests a second, burst 10) and a text-size limit on the server. When a limit is hit, the page offers the sample letters. With CloudFront on, the per-IP key is the `CloudFront-Viewer-Address` header CloudFront adds, and a secret origin header stops callers going around CloudFront. On the live stack, without CloudFront, the origin secret is off and the key falls back to the API Gateway source IP, but a caller who forges `CloudFront-Viewer-Address` can still spread checks across made-up addresses. Until CloudFront is on, the daily cap and the stage throttling are what bound use and cost.
- Tests: pytest covers the reader, every rule, the verdict, the registry, date math, routing, the template explanations in all three languages, and the AI path with Bedrock and Textract faked. `python -m pytest backend/tests -q` runs them.
- Regression tests for false positives: 25 genuine messages (bank OTP alerts, re-KYC notices, police fraud-awareness texts, a jury summons and others) that once read as scams are pinned in `backend/tests/test_false_positives.py`.
- Evaluation on real, government-published examples, scored separately from our own letters, with every miss listed. See the Evaluation section below.
- Operations, defined in the same template: a CloudWatch dashboard, alarms to email through SNS (Lambda errors, p95 duration over 20 s, API 5xx), 14-day log retention and a $10 monthly budget alert.

### Community/Market Impact

Primary users: families in India and the US who deal with official mail in a second language, and the relatives they forward it to. The person who gets the "is this real?" message on the family chat can answer it with a quote and a source instead of a guess.

- Government impersonation is a large and growing loss category in both countries (figures under The problem, sources at the end of this write-up).
- India's Ministry of Home Affairs runs a national awareness campaign on "digital arrest" scams ([MHA, Rajya Sabha unstarred question 1349, 11 Feb 2026](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2026-pdfs/RS11022026/1349.pdf)) and says I4C has blocked more than 3,962 Skype IDs and 83,668 WhatsApp accounts used for them ([PIB, 25 Mar 2025](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2114750)). Plainly's rules flag the pattern directly: arrest threats, CBI or police claims and demands to stay on a video call.
- It costs nothing to use and has no sign-in. With no model in the loop, the running cost is the basic serverless services, so a free tool for individuals is realistic.
- A photo of an official letter is personal data. Reading it on the phone means people don't have to trust a server with it.

### Creativity & Storytelling

The demo opens on two letters that look alike. One is a genuine-format notice and one is a fake, and they get opposite verdicts, each backed by quoted lines and sources. A third sample, the "digital arrest" parcel scam, is the one Indian families are warned about on caller tunes and in the metro.

About two days before the deadline, the AWS account turned out to be on the Free plan, where Bedrock and Textract refuse every call. Rather than drop the entry or pay for an upgrade the owner couldn't make, the reading moved onto the phone and the explanations became written templates. The verdict didn't have to change, because it was already code. Plainly asks the same of a letter as the build asked of itself: check it before trusting it, and keep the receipts.

### How the coding agent helped me ship

| Agent did | I decided | Evidence |
|---|---|---|
| Ran a 22-agent research pass: official rules, judges, 150 competitor projects, past winners, AWS priorities | Which of 18 concepts to build, after a 4-lens weighted score | `docs/research/`, `docs/agent-log.md` |
| Red-teamed its own brief and found 16 issues | Accepted the fixes: an independent reader, split endpoints, redacted injection text, holdout eval | `docs/research/build-brief-and-redteam.md` |
| Wrote the API contract, then built backend, infra, site and docs in parallel against it | Scope cuts (no AgentCore, voice or accounts), the three-verdict design, no "safe" state | `docs/CONTRACT.md` |
| Drafted the official-contacts registry with a source URL and check date per entry | | `backend/registry.json`, `docs/registry-sources.md` |
| Tuned the rules on a dev set of 67 messages, hunted its own false positives, froze the rules by hash and ran the holdout once | Rules stay frozen after the holdout; gaps are listed, not fixed | `eval/RULES_FROZEN.md`, `eval/results.md` |
| Connected to AWS, found the Free plan, captured the exact Bedrock and Textract errors, and wrote an IAM setup script when Claude Code's permission classifier stopped it from creating IAM users itself | Not to upgrade the account; to ship Option B | `docs/agent-log.md`, `infra/setup-agent-user.sh` |
| Re-architected for the Free plan: on-device OCR, rules reader in production, template explanations in three languages, `AI_MODE` switch | "start option b" | `docs/CONTRACT.md` "Option B" |
| Deployed as `plainly-agent`. When CloudFront refused the unverified account, made CloudFront optional and served the site from the Lambda, then ran read-only checks and a guardrail test through the AWS MCP Server | Ran the IAM setup script, published the policy fix, connected the MCP server | `docs/agent-log.md`, `/evidence/` |

The full timestamped log is in [docs/agent-log.md](https://github.com/satanrayshe/plainly/blob/main/docs/agent-log.md).

### Proof of coding agent connection to the AWS console

The coding agent is Claude Code. In AWS it acts as a dedicated IAM user, `plainly-agent`, never as the account root. The owner created that user by running `infra/setup-agent-user.sh`, because Claude Code's permission classifier stopped the agent from creating IAM users itself. The account id is masked as `********1486`. Times are UTC on 2 Oct 2026.

1. Connection. The agent's CLI profile is signed in with `aws login`:

```
$ aws login --region us-east-1 --profile plainly-agent
Updated profile plainly-agent to use arn:aws:iam::********1486:user/plainly-agent credentials.
```

2. AWS MCP Server. The project-scoped entry in `.mcp.json` (no secrets: it names the CLI profile the proxy signs with), then `/mcp` in Claude Code:

```json
"aws-mcp": {
  "type": "stdio",
  "command": "uvx",
  "args": ["mcp-proxy-for-aws-cli@latest", "https://aws-mcp.us-east-1.api.aws/mcp",
           "--metadata", "AWS_REGION=us-east-1"],
  "env": {"AWS_PROFILE": "plainly-agent", "AWS_REGION": "us-east-1"}
}
```

```
/mcp -> Reconnected to aws-mcp.
```

3. Calls the agent made through the MCP server (tool `aws___run_script`), reading back what it had deployed:

```
sts GetCallerIdentity            -> arn:aws:iam::********1486:user/plainly-agent
cloudformation DescribeStacks    -> plainly  UPDATE_COMPLETE  2026-10-02T15:14:04Z
apigatewayv2 GetApis             -> plainly-api  HTTP
lambda ListFunctions             -> plainly-api  python3.13  arm64  1024 MB
dynamodb ListTables              -> plainly-data
cloudwatch DescribeAlarms        -> 4 alarms, all OK
```

4. Guardrail test through the MCP server. The agent's policy denies destructive actions when the call comes through MCP:

```
cloudformation DeleteStack StackName=plainly-mcp-guardrail-test
-> AccessDenied: User: arn:aws:iam::********1486:user/plainly-agent is not authorized to perform:
   cloudformation:DeleteStack on resource:
   arn:aws:cloudformation:us-east-1:********1486:stack/plainly-mcp-guardrail-test/*
   with an explicit deny in an identity-based policy:
   arn:aws:iam::********1486:policy/plainly-agent-policy
```

The same user's `DeleteStack` from the plain CLI at 15:07 UTC, cleaning up the stack CloudFront had blocked, was allowed: the deny is conditioned on `aws:ViaAWSMCPService`.

5. CloudTrail event history (`LookupEvents` for user `plainly-agent`, run through the MCP server):

```
15:16:39  DestroySession    source aws-mcp.amazonaws.com  user agent mcp-proxy-for-aws/1.7.0 claude-code/2.1.287
15:14:04  ExecuteChangeSet  cloudformation                user agent aws-cli/2.37.6
15:11:32  ExecuteChangeSet  cloudformation                user agent aws-cli/2.37.6
15:03:40  ExecuteChangeSet  cloudformation                user agent aws-cli/2.37.6
```

The deploys ran from the agent's shell through the AWS CLI, not through MCP. The MCP server was connected afterwards and used for the read-back and the guardrail test.

6. Gaps. There was no time to set up a dedicated CloudTrail trail with MCP data events, or a deny-only lock policy. The event history above covers management events for 90 days.

The same proof is mirrored on the live site at https://3nf75pgrv4.execute-api.us-east-1.amazonaws.com/evidence/.

### Architecture on AWS

```
Phone / laptop: photo or PDF -> pdf.js text layer or Tesseract.js OCR -> editable text   (photo stays here)
      |
      v  HTTPS, text only
API Gateway HTTP API (HTTPS, stage throttling) -> one Lambda (Python 3.13, arm64, 1024 MB, AI_MODE=off)
      $default route -> static_site.py: the built site from the Lambda package (pre-rendered HTML, sample
                        results, Tesseract.js + pdf.js), with CSP and security headers, clean URLs, gzip
      /api/check     -> rules reader -> 21 rules -> registry (14 agencies) -> date math
      /api/explain   -> written templates, English / Hindi / Spanish
                        DynamoDB (rate limits, daily cap, counters; TTL)
                        CloudWatch Logs (no letter text) -> alarms -> SNS email
Also in the stack: CloudWatch dashboard, a $10 budget alert
In the template, off until AWS verifies the account (UseCloudFront=true): CloudFront + private S3 (OAC) for the pages
Built and switched off: Amazon Textract, Amazon Bedrock (Nova 2 Lite)
```

The live stack has no CloudFront. This is a brand-new AWS Free-plan account, and CloudFront refused to create a distribution: `Your account must be verified before you can add new CloudFront resources.` So the stack runs with `UseCloudFront=false`: API Gateway's `$default` route sends page requests to the same Lambda, which serves the site from its package, and `/api/*` goes to the Lambda's API handler. The CloudFront + S3 setup is still in the template, to switch on once AWS verifies the account.

The full diagram (Mermaid and ASCII), a service table with the reason for each service, and the request flow are in [docs/architecture.md](https://github.com/satanrayshe/plainly/blob/main/docs/architecture.md).

| Measured | Figure |
|---|---|
| Latency: on-device reading and `/api/check` | `/api/check` round trip from India to us-east-1, 12 timed `curl` calls on the live stack: p50 0.76 s, p95 0.87 s. On-device OCR of a sample letter photo: about 2 s in desktop Edge (headless test), longer on phones. The first use also downloads about 7 MB of OCR engine once (8.5 MB with Hindi). |
| AI tokens per letter | 0 (no model call with `AI_MODE=off`) |

### Evaluation

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

### Gotchas

Hit during the build, with exact error text:

- The AWS Free account plan blocks Amazon Bedrock and Amazon Textract. On a new account (`aws freetier get-account-plan-state`: `"accountPlanType": "FREE"`, $100 in credits), every Nova model tried returned `An error occurred (ValidationException) when calling the Converse operation: Operation not allowed`, and Bedrock reported `"authorizationStatus": "NOT_AUTHORIZED"` for Nova 2 Lite even though `list-inference-profiles` listed it. Textract returned `An error occurred (SubscriptionRequiredException) when calling the DetectDocumentText operation: The AWS Access Key Id needs a subscription for the service`. The owner couldn't upgrade, so we re-architected in hours. OCR moved onto the device, which also means the photo never leaves the phone. The verdict was already deterministic code. Explanations became fixed templates, drafted with the coding agent; nothing is generated per letter. The Nova and Textract path is built, passes its tests with the services faked, and is switched off by `AI_MODE`; after an upgrade, `AI_MODE=on scripts/deploy.sh` turns Nova back on for the text the device sends. Textract would also need the page to upload the photo again.
- boto3 can't use `aws login` credentials without the CRT extra. Every call failed with `MissingDependencyException` until `pip install "botocore[crt]"`.
- Claude Code's permission classifier stopped the agent from creating IAM policies and users under the root login ("Permission Grant"), and from probing services under root ("Credential Exploration"). A human decides permission grants, so the agent wrote `infra/setup-agent-user.sh` for the owner to read and run.
- A brand-new Free-plan account can't create CloudFront distributions until AWS verifies it. The stack create was refused with `Your account must be verified before you can add new CloudFront resources.` and rolled back. The agent made CloudFront optional (`UseCloudFront`, default `false`), had the same Lambda serve the site (`backend/static_site.py`), deleted the rolled-back stack and redeployed; the site was live about ten minutes later.
- The first two deploys as `plainly-agent` failed on `apigateway:TagResource`. Removing the stack tags wasn't enough; the permission had to be added to the agent's policy, which the owner published as version 2.

Designed around, from the documentation:

- Tesseract.js runs in a Web Worker with WebAssembly, so the site's Content-Security-Policy has to allow `'wasm-unsafe-eval'` and the worker, and the `.traineddata.gz` language files must be served without a `Content-Encoding: gzip` header, because Tesseract unzips them itself.
- For the CloudFront path (in the template, off on the live stack): an S3 REST origin behind Origin Access Control does not map `/judges/` style paths to `index.html`, which is why a CloudFront Function does the rewrite. Without CloudFront, `backend/static_site.py` does the same mapping.
- API Gateway HTTP APIs stop waiting after 30 seconds, which is why the check and the explanation are separate requests. That mattered most for the model path.
- For the AI path: Nova 2 Lite has no in-Region endpoint in us-east-1, so calls use the `us.amazon.nova-2-lite-v1:0` inference profile and IAM must allow the profile and the model in us-east-1, us-east-2 and us-west-2. Nova 2 Lite supports tool calling but not structured outputs, so extraction is a forced tool call.

### Limitations

- The rules reader matches patterns. It doesn't understand a letter, so scams phrased in ways it doesn't know come out "Can't tell" (1 of 12 holdout scams caught).
- On-device OCR can misread a blurry or skewed photo. The editable text box is there for that, and pasting the text always works.
- The registry covers 14 agencies: 5 in the US, 7 in India and 2 in the UK. For a sender outside it, Plainly can still flag a scam, but the best it can say about a clean letter is "Can't tell".
- Real agencies publish many phone numbers. A genuine number missing from the registry lowers confidence but never produces "Likely scam" on its own.
- Plainly does not visit links or check domain reputation. It compares domains against the registry and looks for lookalikes.
- Explanations come in English, Hindi and Spanish. Any other language falls back to English.
- Hindi letters are read on the device, but the eval has only two Hindi texts, so Hindi accuracy is unmeasured.
- The evaluation set is small. Treat the numbers as a first measurement.
- Plainly is not legal advice. When it says "consistent with genuine", it still tells you to confirm on the official number.

### Where it's headed (Startups)

- Free for individuals. With no model in the loop, a check costs basic serverless usage.
- The paid product would be a white-label "is this real?" check for organisations that already get these calls every day: credit unions and banks, telcos, legal-aid clinics and immigrant-services groups. Each would get its own branding and registry, with the check embedded in its own help channel.
- With a Paid-plan account, `AI_MODE=on` hands the reading of the text to Nova (and to Textract, if the page uploads the photo again), which may catch phrasing the keyword reader misses. Their quotes are still checked in code before they count, and the rules still decide.
- Next features: rules for the holdout gaps (with a fresh holdout to measure them), senders that are not in the registry, intake through WhatsApp where the messages already arrive, voice for people who would rather listen, and more agencies and languages with each entry sourced and dated.

### Category & lane

- Category: #daily-life-enhancement
- Lane: #startups
- Other tags: #aws-lambda, #serverless, #security

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

## Notes for the final pass

- Rules for every edit: no invented numbers, no user counts, no letter content from real people, and never quote the hidden AI instruction from the injection sample.
- Honesty line for every surface (form, site): Bedrock, Textract and Nova are built and switched off on the Free plan. Never say they run in the live product. If the account is upgraded and `AI_MODE=on` is deployed, rewrite the Technical Innovation, Architecture, Gotchas and Evaluation sections, and publish live eval numbers next to the rules-reader ones instead of replacing them.
- The research brief gave the 2024 government-impersonator figure as $789 million, and the red-team said it should be $866 million. The FTC release says $789 million for government impersonators and $866 million for business impersonators, so $789 million is right.
- The IC3 elder figures above come from the PDF itself (elder fraud section, and the age-group chart description on the 2025 complaints page).
- The India figure of ₹22,495 crore for 2025 in the research notes came from a secondary site and does not appear in the MHA replies checked here, so it is not used.
- Keep README.md and this file in sync. The body above was generated from README.md with headings moved down one level, in-page links turned into words and repo links made absolute.
