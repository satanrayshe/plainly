# Plainly infrastructure

One plain CloudFormation stack in **us-east-1**. It has no SAM transform, so Docker and the SAM CLI aren't needed.

```
Browser: reads the letter on the device (pdf.js text layer, else Tesseract.js OCR, eng + hin); the photo never leaves it
   |  only the recognised text, which the reader can review and edit, is sent
   v
CloudFront (PriceClass_100, HTTP/2+3, own response headers policy with a CSP)
             default   -> S3 site bucket (private, OAC) + viewer-request URI rewrite function
             /api/*    -> HTTP API ($default stage, 5 rps / burst 10) -> Lambda python3.13 arm64 1024 MB 29 s
                                                                          -> DynamoDB (rate limits, counters)
                          AI_MODE=off (default): keyword/regex reader + rules + registry + date math + template explanations
                          AI_MODE=on  (Paid plan only): also Textract OCR and Bedrock Nova, built but switched off
CloudWatch: 14-day logs, 4 alarms -> SNS email, dashboard      Budgets: $10/month, email at 50%/100% actual and 100% forecast
```

| File | What it is |
|---|---|
| `template.yaml` | The whole stack: bucket, OAC, CloudFront and its response headers policy, HTTP API, Lambda and role, DynamoDB, SNS, alarms, dashboard, budget |
| `cf-function.js` | Source of the CloudFront Function. The code is inlined in `template.yaml`, and `deploy.sh` refuses to run if the two differ |
| `setup-agent-user.sh` | One-time admin setup (setup steps 1 to 5 below) in one command. Safe to re-run: existing items are reported and left alone |
| `agent-iam-policy.json` | Customer managed policy for the `plainly-agent` IAM user that the coding agent signs in as |
| `plainly-boundary-policy.json` | Permissions boundary that every role the agent creates must carry |
| `agent-lock-policy.json` | Deny-only policy attached to `plainly-agent` once the audit trail is running: the trail, its bucket, log group and delivery role, the alert subscription, alarms and budget can no longer be changed |
| `../scripts/package_lambda.py` | Builds a reproducible Lambda zip: `build/lambda-<sha256[:12]>.zip` |
| `../scripts/deploy.sh` | Package, upload, deploy (or create a change set only), build and sync the site, then invalidate |

## Free plan

The owner's account is on the AWS **Free account plan**. That plan doesn't include Amazon Bedrock (every Nova call
answers `ValidationException: Operation not allowed`) or Amazon Textract (`SubscriptionRequiredException`), so
Plainly ships with **`AI_MODE=off`** (template parameter `AiMode`, default `"off"`):

- Letters are read in the browser (pdf.js text layer, otherwise Tesseract.js OCR). Only the recognised text goes to
  the API.
- The Lambda runs the deterministic engine: keyword/regex reader, verifier rules, registry, date math, and
  template-based explanations in English, Hindi and Spanish. It never creates a Bedrock or Textract client.
- The Lambda role has **no** `bedrock:*` or `textract:*` permission. The two statements are added only when
  `AiMode` is `"on"` (condition `AiOn`).
- The Textract and Nova code is still in the repo. On a Paid-plan account, `AI_MODE=on scripts/deploy.sh` turns it
  back on with no backend change. The site now sends only text, so Nova reads that text; Textract runs only if the
  page is changed to upload the photo again. Until then, describe it as "built, switched off on the Free plan", never as part of
  the live product.

Services the stack uses. All of them are **expected** to be available on the Free plan; the first deploy confirms it:

| Service | Used for |
|---|---|
| AWS Lambda | The `/api/*` handler (python3.13, arm64) |
| Amazon API Gateway (HTTP API) | `/api/*` origin behind CloudFront |
| Amazon CloudFront | Site and API on one origin, URI rewrite function, response headers policy |
| Amazon S3 | Private site bucket, `plainly-artifacts-<account>` for the Lambda zip and templates |
| Amazon DynamoDB | Rate limits, daily cap, anonymous counters (on-demand, TTL) |
| Amazon CloudWatch | Logs (14 days), 4 alarms, 1 dashboard, 1 metric filter |
| Amazon SNS | Alarm emails |
| AWS Budgets | One monthly cost budget, email only |
| AWS CloudFormation, IAM | The stack itself and its roles |

Two things to know about the plan (from the AWS docs, "Choosing a plan"):

- **Don't create or join an AWS Organization** on this account. Joining AWS Organizations automatically moves a
  Free-plan account to the Paid plan. So the old "AI services opt-out policy" step, which needs an organization, is
  **not** part of setup any more. It isn't needed with `AI_MODE=off` either: Textract is never called, so no
  letter image reaches an AWS AI service. (The image doesn't reach AWS at all; it stays in the browser.)
- A Free-plan account closes when its credits run out or after six months, whichever comes first. Everything is paid
  from the credits, so the budget measures cost **before** credits (`IncludeCredit: false`) and warns at 50%.

## One-time account setup (Shrey, as an administrator in the console)

Steps 1 to 5 can be done in one go from Git Bash with an administrator profile:
`ADMIN_PROFILE=plainly-admin bash infra/setup-agent-user.sh`. It asks you to confirm the account, creates what is
missing, reports what already exists, never overwrites a policy (it prints the update command if the file changed),
and shows the new password only on the run that creates the login.

1. **IAM > Policies > Create policy > JSON.** Paste `plainly-boundary-policy.json` and name it exactly **`plainly-boundary`**.
2. Create a second policy from `agent-iam-policy.json` and name it `plainly-agent-policy`.
3. **IAM > Users > Create user** `plainly-agent` with console access. Attach `plainly-agent-policy` and the AWS managed
   policy **`SignInLocalDevelopmentAccess`**, which `aws login` needs. Don't create access keys.
4. Optional but recommended: create a **CloudFormation service role**:
   - Name it `plainly-cfn-deploy`, set the trusted entity to the AWS service CloudFormation, and attach `plainly-agent-policy`.
   - Then export `CFN_ROLE_ARN=arn:aws:iam::<account>:role/plainly-cfn-deploy` before running `deploy.sh`.
   - Why: stack operations then run as the role, not as the agent's session. The MCP-only denies can then never block a rollback or a replacement.
   - The agent can pass this role but can't edit it. Its policy only allows role edits on roles that carry the `plainly-boundary` boundary, and an administrator creates this role without one.
5. Create API Gateway's service-linked role, which the first HTTP API with access logging needs (it is fine if AWS
   says the role already exists). The agent policy also allows exactly this one role, as a fallback.
   ```
   aws iam create-service-linked-role --aws-service-name ops.apigateway.amazonaws.com
   ```
6. **Skip on the Free plan.** (Only for a Paid-plan account that runs `AI_MODE=on`.) Opt the account out of AI
   service data use, so Amazon Textract doesn't keep letter images to improve the service (Bedrock never does):
   **AWS Organizations > Create organization**, then **Policies > AI services opt-out policies > Enable**, and attach
   `{"services": {"default": {"opt_out_policy": {"@@assign": "optOut"}}}}` to the root. Creating the organization
   moves a Free-plan account to the Paid plan, so never do this on the Free plan. With `AI_MODE=off` it isn't needed.
7. In a terminal:
   ```
   aws login --profile plainly-agent --region us-east-1
   aws sts get-caller-identity --profile plainly-agent
   ```
8. **After the agent has created and started the CloudTrail trail** (RUNBOOK step 10): create a policy from
   `agent-lock-policy.json` named `plainly-agent-lock` and attach it to the `plainly-agent` user. From then on the
   agent can't change or stop the trail, touch its bucket, log group or delivery role, or silence the alarm and budget
   emails. It can't detach the lock either: it has no `iam:DetachUserPolicy` or policy-version permissions. Stack
   updates that change the alarms, the topic or the budget must then run with `CFN_ROLE_ARN` (the role doesn't carry
   the lock).
9. **After the first deploy**, narrow CloudFront writes to Plainly's own distribution. In `plainly-agent-policy`,
   replace the `CloudFront` statement's `"Resource": "*"` with:
   ```json
   ["arn:aws:cloudfront::<account>:distribution/<DistributionId from the stack outputs>",
    "arn:aws:cloudfront::<account>:function/plainly-*",
    "arn:aws:cloudfront::<account>:origin-access-control/*",
    "arn:aws:cloudfront::<account>:origin-request-policy/*",
    "arn:aws:cloudfront::<account>:response-headers-policy/*"]
   ```
   Reads (`cloudfront:Get*`, `cloudfront:List*`) stay account-wide through `ReadAnywhere`.

### What the agent policy allows and denies
- **Allows:**
  - CloudFormation on `plainly*` stacks and change sets
  - Lambda, DynamoDB, SNS and S3 on `plainly-*` names
  - HTTP APIs, CloudFront (all distributions until step 9 narrows it) and CloudWatch
  - Logs: full control of `/aws/lambda/plainly-*`, `/aws/apigateway/plainly-*` and `plainly-trail*` log groups only;
    account-wide reads and the log-delivery calls HTTP API access logging needs
  - Budgets: read, and changes to `plainly-*` budgets
  - `iam:CreateServiceLinkedRole` for API Gateway's service-linked role only
  - CloudTrail: read, plus create, update, start and set event selectors on `plainly-*` trails
  - Nova invoke and Bedrock catalog reads, and Textract. These are left in on purpose: they cost nothing while
    `AI_MODE=off` (the Lambda role doesn't get them, and the Free plan refuses the calls anyway), and they let a
    Paid-plan account switch AI on without editing the policy
  - Service Quotas reads, and `freetier:GetAccountPlanState`
  - `sts:GetCallerIdentity`
- **IAM limits:**
  - Role writes are allowed only on `role/plainly-*`, and only when the role carries `policy/plainly-boundary` (condition `iam:PermissionsBoundary`).
  - `iam:PassRole` is allowed only for `plainly-*` roles, and only to Lambda, CloudFormation and CloudTrail. CloudTrail is included so the trail can deliver to CloudWatch Logs.
  - The boundary policy itself can't be changed. `DeleteRolePermissionsBoundary` is denied.
  - `iam:UpdateAssumeRolePolicy` is deliberately not granted. It doesn't support the boundary condition, and with it the agent could make a role trust itself.
- **Explicit Deny when `aws:ViaAWSMCPService` is `true`:**
  - `cloudtrail:StopLogging`, `cloudtrail:DeleteTrail`
  - `cloudformation:DeleteStack`
  - `s3:DeleteBucket`
  - `dynamodb:DeleteTable`
  - `iam:DeleteRole`, `iam:DeleteUser`, `iam:CreateAccessKey`, `iam:CreateUser`, `iam:AttachUserPolicy`

  Per the AWS docs, the AWS MCP Server needs no `aws-mcp:*` actions any more; they are deprecated and have no effect.
- **Always denied:**
  - Writing, overwriting or deleting anything in `plainly-trail-*` buckets, or changing their lifecycle. Name the
    CloudTrail bucket `plainly-trail-<account id>` and turn on versioning when you create it. CloudTrail delivers as a
    service principal, which the agent's policy doesn't affect.
  - Any action outside us-east-1. Global services and Bedrock are exempt, because the `us.` inference profile routes to us-east-2 and us-west-2.
- **Denied once `plainly-agent-lock` is attached (step 8):** everything that could reconfigure or stop the trail (`UpdateTrail`, `PutEventSelectors`, `StopLogging`, `DeleteTrail`), bucket policy, versioning and ACL changes on the trail bucket, deleting or re-routing the trail's log group, editing its delivery role, unsubscribing from the alert topic, and changing alarms or the budget.
- **Before the lock** the agent could still reconfigure the trail it creates. That window is the setup itself; the evidence page says so.
- **Size:** the policy is about 6.06k of the 6,144 non-whitespace characters a managed policy allows. Read-only actions share one `ReadAnywhere` statement to save space.

## Deploy

From Git Bash at the repo root:

```
pip install cfn-lint                                  # optional; deploy.sh lints when it is installed
ALERT_EMAIL=you@example.com scripts/deploy.sh         # first deploy; later runs don't need ALERT_EMAIL
scripts/deploy.sh --site-only                         # site changes only
scripts/deploy.sh --help                              # every option and environment variable
```

- **Profile:** `AWS_PROFILE`, falling back to `plainly-agent`. An administrator profile works too:
  `AWS_PROFILE=plainly-admin scripts/deploy.sh`. If the `plainly-boundary` policy doesn't exist (setup step 1 not
  done), `deploy.sh` stops and says so; as an administrator you can deploy without a boundary with
  `PERMISSIONS_BOUNDARY_ARN= scripts/deploy.sh`.
- **AI mode:** `AI_MODE` (`off` by default, or `on`) becomes the `AiMode` parameter on every deploy and change set.
  A deploy without `AI_MODE=on` therefore always switches AI off. Leave it off on the Free plan.

`deploy.sh` does the following, in order:
1. Checks that `cf-function.js` and the template are in sync, then runs cfn-lint.
2. Resolves the account, checks the default permissions boundary exists, and ensures that `plainly-artifacts-<account>` exists (versioned, BPA, SSE-S3, old versions pruned after 30 days).
3. Packages and uploads the Lambda zip. The key is content-addressed, so an unchanged backend is never re-uploaded or redeployed.
4. Runs `cloudformation deploy` with `CAPABILITY_NAMED_IAM`.
5. Reads the stack outputs, runs `SITE_URL=<SiteUrl> python scripts/build_site.py`, and syncs `dist/` with explicit content types.
6. Invalidates `/*`, curls `/api/health`, and prints `SiteUrl`.

Content types that in-browser OCR depends on (all set explicitly, never guessed):
- `.wasm`: `application/wasm`, which `WebAssembly.instantiateStreaming` requires. (The vendored Tesseract core,
  `vendor/tesseract/core/*.wasm.js`, embeds its WebAssembly in the script, so today no `.wasm` file ships; the rule
  is there for a build that does.)
- `.traineddata.gz` (and plain `.traineddata`): `application/octet-stream`, with **no** `Content-Encoding`.
  Tesseract.js downloads the gzip bytes and gunzips them itself (`gzip: true`). With `Content-Encoding: gzip` the
  browser would unpack them first and Tesseract's own gunzip would fail. CloudFront doesn't compress
  `application/octet-stream`, so the bytes arrive exactly as stored.
- `.js` and `.mjs`: `text/javascript`; `.json`: `application/json`.

Cache headers:
- HTML, JSON and `.ics` files get `no-cache` (JSON under `vendor/` is immutable like the rest of `vendor/`).
- `dist/assets/fonts/` and `dist/vendor/` (pdf.js, Tesseract.js, its wasm core and language data) get
  `public, max-age=31536000, immutable`. Set the list with `IMMUTABLE_DIRS`. Because of that cache, a new library
  version must ship under a new file or folder name (for example `vendor/tesseract/<version>/`).
- Everything else gets `max-age=3600`.

`assets/app.js` and `assets/style.css` aren't fingerprinted, so they stay at one hour. If `build_site.py` starts versioning asset URLs, add `assets` to `IMMUTABLE_DIRS`.

### Response headers (Content-Security-Policy)
The distribution uses its own `plainly-security-headers` policy instead of the managed SecurityHeadersPolicy, which
sets no CSP. The same policy covers the site and `/api/*`:

```
default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self' data:;
img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; object-src 'none';
frame-ancestors 'none'; base-uri 'self'; form-action 'self'
```

- `'wasm-unsafe-eval'` lets Tesseract.js compile its WebAssembly core. Plain `'unsafe-eval'` is not allowed.
- `worker-src blob:` allows Tesseract.js's default `blob:` worker. The site itself loads its workers straight from
  `/vendor/` (`workerBlobURL: false`), which `'self'` covers.
- `connect-src 'self'` means the language data, the wasm core and the API must all be served from this site
  (`/vendor/...`). Nothing is loaded from a CDN. `data:` is there because the Tesseract core (the `*.wasm.js`
  builds, which embed the WebAssembly) first calls `fetch()` on its own `data:` URL. Without it, OCR still works
  through a fallback, but every worker start logs a CSP violation. A `data:` URL can't send anything anywhere.
- Tested locally (Oct 1) in headless Edge against a server sending exactly this CSP and `nosniff`: pdf.js text
  layer and page render, Tesseract.js 5.1.1 eng + hin on a photo and a rendered PDF page, both worker modes, and
  the five built pages. No violations; an external `fetch()` was blocked as it should be.
- `style-src 'unsafe-inline'` is for the `<style>` inside the how-it-works SVG diagram.
- `font-src data:` is for pdf.js, which may load a PDF's embedded fonts as `data:` URLs while rendering pages.
- Also sent: HSTS (one year, subdomains), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, `X-XSS-Protection: 0`,
  `Permissions-Policy: camera=(self), microphone=(), geolocation=(), payment=(), usb=()` and
  `Cross-Origin-Opener-Policy: same-origin`.

If the site ever needs another source (an external script, a CDN, an inline `<script>`), change the CSP in
`template.yaml` in the same change.

### Deploying through the AWS MCP server (for CloudTrail evidence)
`aws cloudformation deploy` from a shell is a CLI call and not an MCP call. To get stack creation attributed to `aws-mcp.amazonaws.com`:

```
scripts/deploy.sh --changeset-only     # uploads zip + template, creates the change set, prints its ARN; executes nothing
```
Then the agent runs these through the MCP server's `call_aws`:
1. `aws cloudformation execute-change-set --change-set-name <ARN>`
2. `aws cloudformation wait stack-create-complete --stack-name plainly` (use `stack-update-complete` for an update)
3. `scripts/deploy.sh --site-only`

If there are no infrastructure changes, the empty change set is deleted and nothing is printed on stdout.

## Verify

```
python -c "import sys; from cfnlint.runner import main; sys.exit(main())" infra/template.yaml   # clean, 0 findings
node -e "const s=require('fs').readFileSync('infra/cf-function.js','utf8'); const h=new Function(s+';return handler')(); for (const u of ['/try','/vendor/tesseract/lang/hin.traineddata.gz','/vendor/tesseract/core/tesseract-core-simd-lstm.wasm.js']) console.log(u, '->', h({request:{uri:u}}).uri)"
# /try -> /try/index.html; the two /vendor/tesseract/ paths come back unchanged
python scripts/package_lambda.py      # prints build/lambda-<hash>.zip; same sources -> same hash
bash -n scripts/deploy.sh && bash scripts/deploy.sh --help
```

After a deploy:
```
curl -sI  https://<SiteUrl>/how-it-works          # 200, text/html (rewritten to /how-it-works/index.html)
curl -sI  https://<SiteUrl>/try/ | grep -i content-security-policy     # the CSP above
curl -sI  https://<SiteUrl>/vendor/tesseract/core/tesseract-core-simd-lstm.wasm.js | grep -i content-type   # text/javascript
curl -sI -H "Accept-Encoding: gzip, br" https://<SiteUrl>/vendor/tesseract/lang/eng.traineddata.gz \
  | grep -i -e content-type -e content-encoding   # application/octet-stream, and no content-encoding line
curl -s   https://<SiteUrl>/api/health            # {"ok": true, ...}
curl -s -o /dev/null -w "%{http_code}\n" <ApiEndpoint>/api/health   # 403: no x-origin-verify header
```
Then check a photo on /try/ in a browser with the developer console open: no CSP violation messages.

## What the backend must honour
- **Environment variables:**
  - `AI_MODE`: `off` (default) or `on`. With `off` the code must never create a boto3 `bedrock-runtime` or
    `textract` client: the role has no permission for either, and the Free plan refuses both.
  - `TABLE_NAME`, `MODEL_IDS` (comma-separated, in order; used only with `AI_MODE=on`), `DAILY_CAP`,
    `RATE_LIMIT_PER_HOUR`, `LOG_LEVEL`
  - `APP_VERSION`: the S3 key of the zip, which works well as the `version` in `/api/health`
  - `ORIGIN_VERIFY` and `IP_HASH_SALT`: random 64-hex values from the NoEcho parameters `OriginVerifySecret` and
    `IpHashSalt`. `deploy.sh` generates them on the first create and keeps them afterwards; set
    `ORIGIN_VERIFY_SECRET` / `IP_HASH_SALT` in the shell only to rotate them. The Lambda logs `ip_hash_salt_unset`
    if the salt is missing.
- **`x-origin-verify`:** CloudFront adds this header to every `/api/*` request. The Lambda should answer 403 when the header is not equal to `ORIGIN_VERIFY`. Without that check, anyone can call the execute-api URL directly with a forged `CloudFront-Viewer-Address` and dodge the per-IP limit.
- **Client IP:** the rate-limit key is `CloudFront-Viewer-Address`, whose value is `ip:port` (IPv6 without brackets), so strip the part after the last `:`. IPv6 viewers are counted per /64, because one home or server holds a whole /64. Only this header, `Content-Type`, `Accept` and `Accept-Language` reach the origin. `X-Forwarded-For` does too, but it is client-controlled, so don't trust it.
- **Bedrock throttling (only with `AI_MODE=on`):** log the botocore error code (`ThrottlingException`) on Bedrock throttling. A metric filter turns those lines into `Plainly/BedrockThrottles`. With AI off the alarm simply stays quiet.
- **DynamoDB:** the Lambda role has only `GetItem`, `PutItem` and `UpdateItem` on the table. Rate-limit and counter items should set `expiresAt` (epoch seconds) so TTL removes them.
- **Packaging:** the zip holds `backend/*.py` (not tests or `conftest.py`) plus `backend/registry.json` and every other `backend/*.json` (for example explanation templates), flat at the root. Data in subfolders is not packaged. `dev_mock.py` ships only if another module imports it. A non-stdlib import other than boto3/botocore fails the build, and so does a module removed in 3.13 such as `cgi`.

## Notes and gotchas
- **No reserved concurrency.** New accounts often have a concurrency limit of 10. Abuse is contained by the stage throttle, the per-IP limit and the daily cap, and the budget alerts on cost.
- **Alarms:**
  - Lambda errors: 3 or more in 5 minutes.
  - API 5xx: 5 or more in 5 minutes. This also counts the app's own 502/503 answers, so it fires when the daily cap is hit.
  - Duration p95: above 20 s.
  - Bedrock throttles: 5 or more in 5 minutes (only possible with `AI_MODE=on`).

  All go to the SNS topic, and **the subscription must be confirmed** from the email that AWS sends after the first deploy.
- **The budget only alerts.** Don't add a Budget action that denies Bedrock, because that would take the live demo down.
- **Git Bash path rewriting:** Git Bash rewrites `/*` into a Windows path when it calls `aws.exe`, so `deploy.sh` sets `MSYS_NO_PATHCONV=1` and passes only relative file paths.
- **Content types:** on Windows the CLI guesses content types from the registry, and `.js` can come out as `text/plain`, which `nosniff` then blocks. That is why the sync uses explicit `--content-type` groups.
- **Clean URLs:** the URI rewrite serves `/try` from `/try/index.html` without a redirect. Pages should therefore reference assets with root-absolute paths (`/assets/app.css`), not relative ones.
- **No custom error responses on the distribution.** They would also rewrite `/api/*` errors. Missing pages return S3's 404, because the bucket policy grants the distribution `s3:ListBucket`.
- **A failed first create** leaves the stack in `ROLLBACK_COMPLETE`, which can only be deleted. `deploy.sh`
  stops with the commands to find the cause and delete the stack; run the delete from your own shell, since
  `DeleteStack` is denied through MCP.
- **New accounts and CloudFront:** a brand-new account can be refused CloudFront resources ("Your account must be
  verified before you can add new CloudFront resources") until AWS Support verifies it, which can take hours to days.
  RUNBOOK step 2 checks this first.
- **Teardown (Shrey, CLI, not through MCP):**
  1. Empty the site bucket.
  2. Run `aws cloudformation delete-stack --stack-name plainly`.
  3. Delete `plainly-artifacts-<account>` if you want to.

## Cost (idle to light demo traffic)
- Lambda, the HTTP API, DynamoDB on-demand, S3 and CloudFront PriceClass_100 all stay within free tier or cost cents.
- Four standard alarms and one dashboard: within the CloudWatch free tier (10 alarms, 3 dashboards).
- With `AI_MODE=off` there is no per-check AI charge: OCR runs on the reader's device and the Lambda runs plain
  code. The biggest item is CloudFront transfer of the OCR language data (a few MB per first visit to /try/,
  then cached by the browser for a year).
- With `AI_MODE=on` (Paid plan), most of the spend is Bedrock and Textract calls per live check.
- The $10 budget measures cost before credits and warns at $5.
