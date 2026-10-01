# Runbook: Option B, from local build to live site

Plainly ships with `AI_MODE=off` because the AWS account is on the Free account plan, which doesn't include Amazon
Bedrock or Amazon Textract (exact errors in `docs/agent-log.md`). The browser reads the letter, and the Lambda runs
the rules reader, the verifier and template explanations. Everything here uses Free-plan services only: Lambda,
API Gateway HTTP API, CloudFront, S3, DynamoDB, CloudWatch, SNS and Budgets.

Run the commands from Git Bash at the repo root, in us-east-1. Before any step that acts on AWS, check which
account you're signed in to (step 1). Only Shrey's account is allowed.

## 0. Local checks (no AWS)

```bash
python -m pytest backend/tests -q                      # all green
python scripts/run_samples.py                           # production rules path -> samples/results/<id>.json, "mock": false
python scripts/build_site.py --strict                   # refuses to build if any landing sample is mock
python scripts/dev_server.py                            # http://127.0.0.1:8000, AI_MODE=off
python eval/run_eval.py --set all --out eval/results-rules-reader.md
```

The eval numbers must match `eval/results.md` (dev 25/29, holdout 1/12, synthetic 11/12, no scam marked genuine,
no genuine letter marked scam). If they don't, the reader or the rules changed; stop and find out why before
publishing any number.

On `/try/`, upload `samples/letters/irs-balance-due.png` and check that the text appears in the edit box before the
check runs, and that the verdict and the Hindi and Spanish explanations render.

## 1. Identity: who deploys

Pick one:

- **Recommended: the restricted agent user.** Shrey runs the one-time setup as the account administrator:
  ```bash
  aws login --profile plainly-admin --region us-east-1     # Shrey signs in in the browser
  bash infra/setup-agent-user.sh                           # policies, plainly-agent user, plainly-cfn-deploy role
  aws login --profile plainly-agent --region us-east-1     # sign in with the details the script prints
  export AWS_PROFILE=plainly-agent
  ```
  The agent can't do this part itself. Claude Code's permission classifier blocked it from creating IAM policies
  and users, because granting permissions is a human decision.
- **Fallback: Shrey's admin profile.** `export AWS_PROFILE=plainly-admin`. It works, but the audit story is weaker
  (every call is the root or admin identity), and the classifier may block the agent from some calls under it.

Then confirm the account:

```bash
aws sts get-caller-identity          # account must end in 1486; mask it everywhere you publish it
```

Save the masked output for `/evidence/`.

## 2. Deploy with AI_MODE=off

Before the first deploy, two things, in this order:

1. **CloudFront pre-check (Shrey, console, 2 minutes).** Brand-new accounts are often refused CloudFront resources
   ("Your account must be verified before you can add new CloudFront resources") until AWS Support verifies them,
   which can take hours to days. Without a check, the first deploy finds out, and the stack is left in
   `ROLLBACK_COMPLETE` and has to be deleted from your own shell. To check without a stack: in the CloudFront console,
   create a distribution with any origin (for example `example.com`). If AWS refuses, open a Support case at once
   and do steps 3 and 4's non-CloudFront parts meanwhile. If it is created, disable it and delete it once it shows
   as disabled; a disabled distribution costs nothing in the meantime.
2. **Decide how the stack is created.** For CloudTrail to attribute the stack creation to the AWS MCP Server, connect
   the MCP server first (the first bullet of step 4 says how) and use the change-set route at the end of this step.
   A stack created by the plain command below is a CLI call, and its creation can't be re-attributed later.

```bash
AI_MODE=off ALERT_EMAIL=<shrey's email> scripts/deploy.sh
```

`AI_MODE` defaults to `off`, and deploy.sh sends it on every deploy, so a later deploy without `AI_MODE=on` keeps AI
off. `ALERT_EMAIL` is needed only on the first create. With the `plainly-agent` profile, add
`CFN_ROLE_ARN=arn:aws:iam::<account>:role/plainly-cfn-deploy` so stack operations run as the deploy role.

Don't set up the AI services opt-out policy (the old step 6 in `infra/README-infra.md`). It is only about Textract,
which isn't called, and it needs AWS Organizations. See the Free plan section in `infra/README-infra.md`.

Things that can go wrong on a new account:

- CloudFront refuses to create the distribution ("Your account must be verified before you can add new CloudFront
  resources"), if the pre-check above was skipped. Open an AWS Support case at once. The stack rolls back.
- The first create fails for any reason. The stack is left in `ROLLBACK_COMPLETE`, which can only be deleted. Find
  the cause, delete it from your own shell, fix and rerun:
  ```bash
  aws cloudformation describe-stack-events --stack-name plainly \
    --query "StackEvents[?ResourceStatus=='CREATE_FAILED'].[LogicalResourceId,ResourceStatusReason]"
  aws cloudformation delete-stack --stack-name plainly && aws cloudformation wait stack-delete-complete --stack-name plainly
  ```
- A Free-plan restriction on one of the services. None is expected, but the first deploy is the real test. Record
  the exact error in `docs/agent-log.md`.

Confirm the SNS subscription email afterwards, or no alarm email ever arrives.

To have the stack change attributed to the AWS MCP Server in CloudTrail (MCP connected first, see above), use
`scripts/deploy.sh --changeset-only`, execute the printed change set through MCP (`aws cloudformation execute-change-set`, then `wait
stack-create-complete`), and publish the site with `scripts/deploy.sh --site-only`.

## 3. Verify

```bash
SITE=<SiteUrl from the deploy output>
for p in / /try/ /how-it-works/ /evidence/ /judges/ /assets/og.png; do curl -s -o /dev/null -w "%{http_code} $p\n" "$SITE$p"; done
curl -s "$SITE/api/health"                                                          # {"ok": true, ..., "ai_mode": "off"}
curl -sI "$SITE/vendor/tesseract/lang/eng.traineddata.gz" | grep -i "^content-\(type\|encoding\)"   # octet-stream, no gzip encoding
curl -s -o /dev/null -w "%{http_code} direct API (expect 403)\n" "<ApiEndpoint>/api/health"
curl -s -X POST "$SITE/api/check" -H 'content-type: application/json' \
  -d '{"text":"Pay the fine today with Google Play gift cards or you will be arrested.","text_source":"typed"}' | head -c 300
```

Then, in a signed-out browser on a phone:

- Open each landing sample.
- Photograph a printed sample letter on `/try/`. The OCR progress bar should run, the text should appear for review,
  and the verdict should match `samples/README.md`. Note the time the reading took.
- Paste an SMS, and switch the explanation to हिन्दी and Español.
- Open DevTools and check that nothing is blocked by the Content-Security-Policy (Tesseract needs a blob worker and
  WebAssembly).

Fill `{{LATENCY}}` in `README.md`, `docs/SUBMISSION.md` and `docs/architecture.md` with the measured on-device OCR
time and `/api/check` p50/p95 (CloudWatch `Duration`, or timed curl calls).

## 4. Capture the evidence

- The masked `sts get-caller-identity` from step 1, and the `aws login` transcript.
- Connect the AWS MCP Server if it isn't yet. Proof of coding agent connection to the AWS console is a pass/fail
  ship gate, and the Agent Toolkit flow (`aws configure agent-toolkit`, or `claude mcp add` for
  `https://aws-mcp.us-east-1.api.aws/mcp`) is the most literal reading of it (`docs/research/rules.md`). Capture the
  Claude Code MCP config, `/mcp` showing it connected, and one read call on the deployed stack through MCP with its
  request id.
- CloudTrail: create the bucket `plainly-trail-<account id>` with versioning on, and attach CloudTrail's bucket
  policy **before** `CreateTrail` (without it CreateTrail fails with `InsufficientS3BucketPolicyException`): allow
  the service principal `cloudtrail.amazonaws.com` `s3:GetBucketAcl` on the bucket and `s3:PutObject` on
  `arn:aws:s3:::plainly-trail-<account id>/AWSLogs/<account id>/*` with the condition
  `"s3:x-amz-acl": "bucket-owner-full-control"` (both statements also with `aws:SourceArn` =
  `arn:aws:cloudtrail:us-east-1:<account id>:trail/plainly-trail`). Then create and start the `plainly-trail`
  trail. Once it logs, Shrey attaches `plainly-agent-lock` (`infra/README-infra.md`, setup step 8). Then look up the
  stack events:
  ```bash
  aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=ExecuteChangeSet --max-results 5
  ```
- `/api/health` output showing `"ai_mode": "off"`.
- Fill the boxes in `site/evidence/index.html` and the `{{AGENT_PROOF}}` block in `README.md` and
  `docs/SUBMISSION.md`, add rows to `docs/agent-log.md`, then `scripts/deploy.sh --site-only`.
- Before publishing anything, mask the account id and every stack ARN or stack UUID. Never publish
  `describe-stacks` parameters, Lambda environment variables or the distribution config: they hold the origin-verify
  secret and the IP-hash salt.

Commit locally with `python -m pytest backend/tests -q` green. Push to the public repo on the satanrayshe account
only when Shrey says so.

## 5. Optional: if the account is ever upgraded (AI_MODE=on)

Only after Shrey moves the account to the Paid plan himself. Nothing in this project does that.

```bash
python scripts/smoke_bedrock.py                     # expect: OK us.amazon.nova-2-lite-v1:0: mode=tool ...
aws textract detect-document-text --document "Bytes=fileb://samples/letters/irs-balance-due.png" \
  --query "length(Blocks[?BlockType=='LINE'])"
AI_MODE=on scripts/deploy.sh                          # adds Bedrock + Textract to the Lambda role
curl -s "$SITE/api/health"                            # "ai_mode": "on"
```

- boto3 needs `pip install "botocore[crt]"` to use `aws login` credentials; without it every call fails with
  `MissingDependencyException`.
- With AI on, do the AI services opt-out (setup step 6 in `infra/README-infra.md`) so Textract doesn't keep images.
- Re-run the sample results and the eval in live mode and publish those numbers next to the rules-reader ones,
  labelled as a different reader: `python scripts/run_samples.py --live`,
  `python eval/run_eval.py --live --out eval/results-live.md`.
- Update the write-up: the "switched off" wording in `README.md`, `docs/SUBMISSION.md`, `docs/architecture.md` and
  the site becomes wrong the moment AI is on.

Going back is `AI_MODE=off scripts/deploy.sh`.
