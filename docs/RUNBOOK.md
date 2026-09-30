# Runbook: from offline build to live site

Everything up to step 0 already works offline (tests, mock dev server, offline samples and eval). This file lists
the commands to run once AWS is connected, in order. Run them from Git Bash at the repo root.
`PROFILE=plainly-agent` and region `us-east-1` throughout.

Before any step that acts on AWS, check which account you're signed in to (step 1). Only Shrey's account is
allowed.

## 0. Where things stand before AWS

| Item | State | Replaced by |
|---|---|---|
| `samples/results/electricity-final-notice.json`, `irs-balance-due.json`, `digital-arrest-parcel.json` | Hand-written placeholders, `"mock": true` | Step 5 overwrites them |
| `samples/results/mock/*.json` (all six) | Offline pipeline run with fake Textract/Bedrock, `"mock": true` | Only used when `samples/results/<id>.json` is missing |
| `eval/results-offline.md` | Offline wiring check (keyword reader, not the model) | Step 9 writes `eval/results.md` |
| `/evidence/` page | Five placeholder boxes | Step 10 |

The site marks every mock result on the page ("Illustrative result, not from the live checker..."), and
`scripts/deploy.sh` builds with `--strict`, which refuses to publish while any sample is mock. Set
`ALLOW_MOCK_SAMPLES=1` only for a throwaway infrastructure test.

## 1. Connect and confirm the identity

One-time admin setup (policies, `plainly-agent` user, optional `plainly-cfn-deploy` role) is in
`infra/README-infra.md`. Then:

```bash
aws login --profile plainly-agent --region us-east-1
aws sts get-caller-identity --profile plainly-agent      # Arn must end in :user/plainly-agent in Shrey's account
export AWS_PROFILE=plainly-agent AWS_REGION=us-east-1
```

Connect the AWS MCP Server in Claude Code with `AWS_MCP_PROXY_PROFILES=plainly-agent` and check `/mcp` shows it
connected. Save the masked `get-caller-identity` output and the `/mcp` line for `/evidence/`.

## 2. Account plan and quotas

```bash
aws freetier get-account-plan-state                           # a "free" plan can block Bedrock; upgrade in Billing if so
aws bedrock list-inference-profiles --query "inferenceProfileSummaries[?contains(inferenceProfileId,'nova')].inferenceProfileId"
aws service-quotas list-service-quotas --service-code bedrock \
  --query "Quotas[?contains(QuotaName,'Nova')].[QuotaName,Value]" --output table
aws lambda get-account-settings --query "AccountLimit.ConcurrentExecutions"
aws service-quotas list-service-quotas --service-code textract --query "Quotas[].[QuotaName,Value]" --output table
```

Look for `us.amazon.nova-2-lite-v1:0` in the profiles, non-zero requests-per-minute and tokens-per-minute quotas for
Nova 2 Lite (and Nova Pro / Lite, the fallbacks), and note the Lambda concurrency limit (often 10 on new accounts,
which is fine for the demo).

## 3. Smoke test Bedrock: image + forced tool

```bash
python scripts/smoke_bedrock.py
```

Sends the IRS sample letter as a JPEG with the forced `record_letter` tool to each model in the chain, using
the Lambda's own code. Expected: `OK us.amazon.nova-2-lite-v1:0: mode=tool ...`.

- `mode=any`: the model rejected `toolChoice: {"tool": ...}` and the automatic downgrade to `{"any": {}}` worked.
  Fine, note it in `docs/agent-log.md`.
- `AccessDeniedException`: model access or the account plan (step 2).
- `ValidationException` naming the schema: the tool schema needs a fix in `backend/pipeline.py`; rerun
  `python -m pytest backend/tests -q` after.

Textract check (optional, the next step exercises it too):

```bash
aws textract detect-document-text --document "Bytes=fileb://samples/letters/irs-balance-due.png" \
  --query "length(Blocks[?BlockType=='LINE'])"
```

## 4. Freeze the rules

From here on, don't edit `backend/verifier.py`, `lexicon.py`, `contacts.py` or `registry.json` without
re-running steps 5 and 9. The eval report records sha256 prefixes of `verifier.py` and `registry.json`, so a
published number is tied to one rules version.

## 5. Live sample results

```bash
python scripts/run_samples.py --live
```

Writes `samples/results/<id>.json` (`"mock": false`) for all six letters, with English, Hindi and Spanish
explanations, overwriting the hand-written placeholders. The script drops `letter_text` and refuses to save a
result that repeats the hidden AI line. Compare the verdicts with the expected ones in `samples/README.md`.
If a genuine-format sample comes out "Can't tell", read its `unknown_contact` trace line before changing anything.

## 6. Rebuild and preview

```bash
python scripts/build_site.py --strict        # fails if any sample is still mock
python scripts/dev_server.py --live          # optional local preview against real AWS, http://127.0.0.1:8000
```

## 7. Deploy through a change set

```bash
export CFN_ROLE_ARN=arn:aws:iam::<account>:role/plainly-cfn-deploy     # recommended, see infra/README-infra.md
ALERT_EMAIL=<shrey's email> scripts/deploy.sh --changeset-only          # prints the change set ARN; runs nothing
```

Then, through the MCP server (`call_aws`), so CloudTrail attributes it to MCP:

1. `aws cloudformation execute-change-set --change-set-name <ARN>`
2. `aws cloudformation wait stack-create-complete --stack-name plainly` (`stack-update-complete` on later runs)

Then publish the site from the shell (builds with `--strict`, syncs, invalidates, checks `/api/health`):

```bash
scripts/deploy.sh --site-only
```

Confirm the SNS subscription email, or no alarm email ever arrives.

## 8. Verify the live site

```bash
SITE=<SiteUrl from the deploy output>
for p in / /try/ /how-it-works/ /evidence/ /judges/ /assets/og.png; do curl -s -o /dev/null -w "%{http_code} $p\n" "$SITE$p"; done
curl -s "$SITE/api/health"
curl -s -o /dev/null -w "%{http_code} direct API (expect 403)\n" "<ApiEndpoint>/api/health"
```

Then in a signed-out browser: open each landing sample, check one real letter photo on a phone, and one pasted SMS.

## 9. Live eval

```bash
python eval/run_eval.py --live               # -> eval/results.md (holdout and synthetic reported separately)
```

About 47 checks plus explanations, a few cents. It runs in-process, so it does not use the deployed daily cap
unless `TABLE_NAME` is set in your shell. Copy the tables into `{{EVAL_TABLE}}` / `{{EVAL_SUMMARY}}` in
`README.md` and `docs/SUBMISSION.md`, and the latency and token figures into `{{LATENCY_*}}`,
`{{TOKENS_PER_LETTER}}` and `{{COST_PER_LETTER}}`.

## 10. Fill the evidence

- CloudTrail: create the trail through MCP (bucket named `plainly-trail-<account id>`; the agent policy denies
  deleting objects in it), then capture events whose source is `aws-mcp.amazonaws.com`:
  ```bash
  aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=ExecuteChangeSet --max-results 5
  ```
- Deny policy proof: one MCP call that the explicit deny blocks (for example `cloudformation delete-stack` on a
  stack that doesn't exist), with the `AccessDenied` message.
- Fill the five boxes in `site/evidence/index.html`, the `{{AGENT_PROOF}}` block and `{{CONFIRM: ...}}` items in
  `docs/SUBMISSION.md` / `README.md`, the rows after deploy in `docs/agent-log.md`, then `scripts/deploy.sh --site-only`.
- If the real MCP setup differs from what `/evidence/` and step 5 of `/judges/` describe, rewrite those sentences.

## 11. Commit and publish the repo

```bash
python -m pytest backend/tests -q
git add -A && git commit -m "Live sample results, eval and evidence"
```

Push to the public repo on the satanrayshe account only when Shrey says so.
