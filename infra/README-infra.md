# Plainly infrastructure

One plain CloudFormation stack in **us-east-1**. It has no SAM transform, so Docker and the SAM CLI aren't needed.

```
Browser -> CloudFront (PriceClass_100, HTTP/2+3, security headers)
             default   -> S3 site bucket (private, OAC) + viewer-request URI rewrite function
             /api/*    -> HTTP API ($default stage, 5 rps / burst 10) -> Lambda python3.13 arm64 1024 MB 29 s
                                                                          -> Textract, Bedrock Nova (us. profile), DynamoDB
CloudWatch: 14-day logs, 4 alarms -> SNS email, dashboard      Budgets: $10/month, email at 50%/100% actual and 100% forecast
```

| File | What it is |
|---|---|
| `template.yaml` | The whole stack: bucket, OAC, CloudFront, HTTP API, Lambda and role, DynamoDB, SNS, alarms, dashboard, budget |
| `cf-function.js` | Source of the CloudFront Function. The code is inlined in `template.yaml`, and `deploy.sh` refuses to run if the two differ |
| `agent-iam-policy.json` | Customer managed policy for the `plainly-agent` IAM user that the coding agent signs in as |
| `plainly-boundary-policy.json` | Permissions boundary that every role the agent creates must carry |
| `../scripts/package_lambda.py` | Builds a reproducible Lambda zip: `build/lambda-<sha256[:12]>.zip` |
| `../scripts/deploy.sh` | Package, upload, deploy (or create a change set only), build and sync the site, then invalidate |

## One-time account setup (Shrey, as an administrator in the console)

1. **IAM > Policies > Create policy > JSON.** Paste `plainly-boundary-policy.json` and name it exactly **`plainly-boundary`**.
2. Create a second policy from `agent-iam-policy.json` and name it `plainly-agent-policy`.
3. **IAM > Users > Create user** `plainly-agent` with console access. Attach `plainly-agent-policy` and the AWS managed
   policy **`SignInLocalDevelopmentAccess`**, which `aws login` needs. Don't create access keys.
4. Optional but recommended: create a **CloudFormation service role**:
   - Name it `plainly-cfn-deploy`, set the trusted entity to the AWS service CloudFormation, and attach `plainly-agent-policy`.
   - Then export `CFN_ROLE_ARN=arn:aws:iam::<account>:role/plainly-cfn-deploy` before running `deploy.sh`.
   - Why: stack operations then run as the role, not as the agent's session. The MCP-only denies can then never block a rollback or a replacement.
   - The agent can pass this role but can't edit it. Its policy only allows role edits on roles that carry the `plainly-boundary` boundary, and an administrator creates this role without one.
5. In a terminal:
   ```
   aws login --profile plainly-agent --region us-east-1
   aws sts get-caller-identity --profile plainly-agent
   ```

### What the agent policy allows and denies
- **Allows:**
  - CloudFormation on `plainly*` stacks and change sets
  - Lambda, DynamoDB, SNS and S3 on `plainly-*` names
  - HTTP APIs, CloudFront, Logs and CloudWatch
  - Budgets
  - CloudTrail: read, plus create, update, start and set event selectors on `plainly-*` trails
  - Nova invoke and Bedrock catalog reads
  - Textract
  - Service Quotas reads
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
  - Deleting objects or changing the lifecycle in `plainly-trail-*` buckets. Name the CloudTrail bucket `plainly-trail-<account id>`.
  - Any action outside us-east-1. Global services and Bedrock are exempt, because the `us.` inference profile routes to us-east-2 and us-west-2.
- **Size:** the policy is about 5.8k of the 6,144 non-whitespace characters a managed policy allows.

## Deploy

From Git Bash at the repo root:

```
pip install cfn-lint                                  # optional; deploy.sh lints when it is installed
ALERT_EMAIL=you@example.com scripts/deploy.sh         # first deploy; later runs don't need ALERT_EMAIL
scripts/deploy.sh --site-only                         # site changes only
```

`deploy.sh` does the following, in order:
1. Checks that `cf-function.js` and the template are in sync, then runs cfn-lint.
2. Resolves the account and ensures that `plainly-artifacts-<account>` exists (versioned, BPA, SSE-S3, old versions pruned after 30 days).
3. Packages and uploads the Lambda zip. The key is content-addressed, so an unchanged backend is never re-uploaded or redeployed.
4. Runs `cloudformation deploy` with `CAPABILITY_NAMED_IAM`.
5. Reads the stack outputs, runs `SITE_URL=<SiteUrl> python scripts/build_site.py`, and syncs `dist/` with explicit content types.
6. Invalidates `/*`, curls `/api/health`, and prints `SiteUrl`.

Cache headers:
- HTML, JSON and `.ics` files get `no-cache`.
- `dist/assets/fonts/` and `dist/vendor/` get `public, max-age=31536000, immutable`. Set the list with `IMMUTABLE_DIRS`.
- Everything else gets `max-age=3600`.

`assets/app.js` and `assets/style.css` aren't fingerprinted, so they stay at one hour. If `build_site.py` starts versioning asset URLs, add `assets` to `IMMUTABLE_DIRS`.

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
node -e "const s=require('fs').readFileSync('infra/cf-function.js','utf8'); const h=new Function(s+';return handler')(); console.log(h({request:{uri:'/try'}}).uri)"
python scripts/package_lambda.py      # prints build/lambda-<hash>.zip; same sources -> same hash
bash scripts/deploy.sh --help
```

After a deploy:
```
curl -sI  https://<SiteUrl>/how-it-works          # 200, text/html (rewritten to /how-it-works/index.html)
curl -s   https://<SiteUrl>/api/health            # {"ok": true, ...}
curl -s -o /dev/null -w "%{http_code}\n" <ApiEndpoint>/api/health   # 403 once app.py enforces ORIGIN_VERIFY
```

## What the backend must honour
- **Environment variables:**
  - `TABLE_NAME`, `MODEL_IDS` (comma-separated, in order), `DAILY_CAP`, `RATE_LIMIT_PER_HOUR`, `LOG_LEVEL`
  - `APP_VERSION`: the S3 key of the zip, which works well as the `version` in `/api/health`
  - `ORIGIN_VERIFY`
- **`x-origin-verify`:** CloudFront adds this header to every `/api/*` request. The Lambda should answer 403 when the header is not equal to `ORIGIN_VERIFY`. Without that check, anyone can call the execute-api URL directly with a forged `CloudFront-Viewer-Address` and dodge the per-IP limit.
- **Client IP:** the rate-limit key is `CloudFront-Viewer-Address`, whose value is `ip:port` (IPv6 without brackets), so strip the part after the last `:`. Only this header, `Content-Type`, `Accept` and `Accept-Language` reach the origin. `X-Forwarded-For` does too, but it is client-controlled, so don't trust it.
- **Bedrock throttling:** log the botocore error code (`ThrottlingException`) on Bedrock throttling. A metric filter turns those lines into `Plainly/BedrockThrottles`.
- **DynamoDB:** the Lambda role has only `GetItem`, `PutItem` and `UpdateItem` on the table. Rate-limit and counter items should set `expiresAt` (epoch seconds) so TTL removes them.
- **Packaging:** the zip holds `backend/*.py` (not tests or `conftest.py`) plus `backend/registry.json`, flat at the root. `dev_mock.py` ships only if another module imports it. A non-stdlib import other than boto3/botocore fails the build, and so does a module removed in 3.13 such as `cgi`.

## Notes and gotchas
- **No reserved concurrency.** New accounts often have a concurrency limit of 10. Abuse is contained by the stage throttle, the per-IP limit and the daily cap, and the budget alerts on cost.
- **Alarms:**
  - Lambda errors: 3 or more in 5 minutes.
  - API 5xx: 5 or more in 5 minutes. This also counts the app's own 502/503 answers, so it fires when the daily cap is hit.
  - Duration p95: above 20 s.
  - Bedrock throttles: 5 or more in 5 minutes.

  All go to the SNS topic, and **the subscription must be confirmed** from the email that AWS sends after the first deploy.
- **The budget only alerts.** Don't add a Budget action that denies Bedrock, because that would take the live demo down.
- **Git Bash path rewriting:** Git Bash rewrites `/*` into a Windows path when it calls `aws.exe`, so `deploy.sh` sets `MSYS_NO_PATHCONV=1` and passes only relative file paths.
- **Content types:** on Windows the CLI guesses content types from the registry, and `.js` can come out as `text/plain`, which `nosniff` then blocks. That is why the sync uses explicit `--content-type` groups.
- **Clean URLs:** the URI rewrite serves `/try` from `/try/index.html` without a redirect. Pages should therefore reference assets with root-absolute paths (`/assets/app.css`), not relative ones.
- **No custom error responses on the distribution.** They would also rewrite `/api/*` errors. Missing pages return S3's 404, because the bucket policy grants the distribution `s3:ListBucket`.
- **Teardown (Shrey, CLI, not through MCP):**
  1. Empty the site bucket.
  2. Run `aws cloudformation delete-stack --stack-name plainly`.
  3. Delete `plainly-artifacts-<account>` if you want to.

## Cost (idle to light demo traffic)
- Lambda, the HTTP API, DynamoDB on-demand, S3 and CloudFront PriceClass_100 all stay within free tier or cost cents.
- Four standard alarms and one dashboard: about $0.40/month for the alarms. The first three dashboards are free.
- Most of the spend is Bedrock and Textract calls per live check. The $10 budget warns at $5 actual.
