# Build log

A timestamped record of what the coding agent (Claude Code) did, what Shrey decided, and where the evidence is. Times are IST (UTC+5:30). Paths are relative to the repo root unless marked as the session scratchpad.

Entries before 19:30 on 30 Sep were written after the fact from file timestamps and the research documents, so their times are approximate. Shrey should check the "Human decided" column for those rows and correct the wording where it differs from what he actually said.

## Wednesday 30 Sep 2026

| Time (IST) | Agent did | Human decided | Evidence |
|---|---|---|---|
| ~18:37 | Session started in the project folder. A prior Plainly draft (a single Lambda handler that explained letters with Nova, with a 7-day share feature) was already in `backend/`. | Enter AWS Zero to Shipped with this project folder as the base | `backend/app.py` (timestamp 18:40) |
| ~18:44 to ~19:06 | Research workflow of 22 agents. They read the official rules, FAQ and terms; the five judges' public profiles; all 150 projects in the public gallery through its submissions API plus about 45 in-progress GitHub entries; past winners; and current AWS priorities (Agent Toolkit for AWS, AWS MCP Server, Nova 2 Lite). | | `docs/research/rules.md`, `docs/research/official.json`, `docs/research/competitors.md`; raw pages and API dumps in the session scratchpad (`comp/subs.json`, `readmes.json`) |
| ~19:06 to ~19:20 | Generated 18 concepts and scored each with four weighted lenses, one per judging criterion (25% each). Merged the top ideas (C1's fake-vs-genuine letters, C16's visible receipts and C13's quoted evidence for every flag) into one brief. | Accepted the pick: keep Plainly and put the scam check first. Rejected Payhold (C10): best originality score (8.0) but feasibility 6.5, with a domain pivot and DNS and RDAP lookups too flaky for about 65 solo hours. Cut AgentCore, Nova Sonic and Nova Act to the roadmap. | `docs/research/build-brief-and-redteam.md`, sections 1 and 2 |
| ~19:20 | Red-teamed its own brief and found 16 issues (5 high). Verdict: GO with fixes. | Accepted all 13 required fixes: Textract as an independent reader and no model transcript; `/api/check` and `/api/explain` split to stay under the 30-second API limit; the hidden AI instruction redacted everywhere and kept off the landing page; rate limit keyed on `CloudFront-Viewer-Address` plus a daily cap; a CloudFront Function for page paths; honest MCP wording; a holdout eval on government-published scams; a comparison with Norton Genie and Scamio; a narrower persona (families handling official mail in a second language, India and US) with a domain-first registry; pdf.js for PDFs; checks on account plan and ownership; real testers with n; cited figures corrected. | `docs/research/build-brief-and-redteam.md`, "REDTEAM" section |
| ~19:21 | Saved the research outputs into the repo. | | `docs/research/` (timestamps 19:22) |
| 19:23 | Wrote the build contract: repo layout, HTTP API shapes, the 13 verifier rules and their severities, the verdict formula, extract tool fields, pages, design direction, privacy rules. | Category #daily-life-enhancement, lane #startups. The share feature is removed. Three verdicts with no "safe" state. | `docs/CONTRACT.md` |
| ~19:25 | Started parallel builders, each limited to its own area of the repo and coding against the contract: backend, infra and scripts, site, samples and eval, docs. No AWS calls and no pushes during this phase. | Build locally first; connect the agent to AWS and deploy after | This log; files under each area |
| 19:29 onward | Docs agent checked every impact figure on its primary page before using it. The FTC release gives government-impersonator losses of about $920 million in 2025, up from $789 million in 2024; the red-team's $866 million correction was wrong (that figure is business impersonators). IC3 elder figures were confirmed from the PDF text. India figures were taken only from MHA parliamentary replies and a PIB release; the ₹22,495 crore figure from a secondary site was dropped. Fetched the Norton Genie and Bitdefender Scamio pages for the comparison. | | `docs/SUBMISSION.md` ("Sources for the figures", "Notes for the final pass"), `docs/comparison.md` |
| 19:29 onward | Docs agent wrote the README, submission draft, architecture (Mermaid plus ASCII), comparison, this log, LICENSE and `.gitignore`. Description counted in code at 505 of 512 characters, with no words shared with the title. | | `README.md`, `docs/SUBMISSION.md`, `docs/architecture.md`, `docs/comparison.md`, `LICENSE`, `.gitignore` |

## Next entries

Add a row for each of these as they happen, with the exact command or transcript excerpt and the path of the saved output:

- Agent connection: `aws login`, `aws configure agent-toolkit`, `/mcp` showing aws-mcp connected, the "What AWS Regions are available?" answer.
- CloudTrail trail with AWS MCP data events, created through MCP.
- Bedrock smoke tests: Nova 2 Lite with an image, forced tool choice, and any exact error text for the Gotchas section.
- First deploy, the live URL, and `curl` checks of every page path.
- Builder Center project published (first version).
- Any incident the agent diagnosed from CloudWatch Logs, with the query it ran and the fix commit.
- Eval runs, before and after fixes.
