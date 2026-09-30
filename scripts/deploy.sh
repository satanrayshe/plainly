#!/usr/bin/env bash
# Deploy Plainly to us-east-1: Lambda zip -> CloudFormation stack -> static site -> CDN invalidation.
#
#   ALERT_EMAIL=you@example.com scripts/deploy.sh   full deploy (ALERT_EMAIL is required only on first create)
#   scripts/deploy.sh --changeset-only              upload artifacts, create a change set, print its ARN;
#                                                   nothing is executed (run it through the AWS MCP server)
#   scripts/deploy.sh --site-only                   rebuild dist/ and publish it to the existing stack
#
# Environment (all optional unless noted):
#   AWS_PROFILE               default plainly-agent
#   STACK_NAME, APP_NAME      default plainly (the agent IAM policy only covers plainly* names)
#   ALERT_EMAIL               alarm + budget emails; required when the stack does not exist yet
#   PERMISSIONS_BOUNDARY_ARN  default arn:aws:iam::<account>:policy/plainly-boundary; set to "" for none
#   CFN_ROLE_ARN              CloudFormation service role to run stack operations as
#   MODEL_IDS, DAILY_CAP, RATE_LIMIT_PER_HOUR, LOG_LEVEL, MONTHLY_BUDGET_USD   template parameter overrides
#   ORIGIN_VERIFY_SECRET, IP_HASH_SALT   set only to rotate them; generated on first create, then kept
#   PYTHON                    interpreter for the helper scripts
#   IMMUTABLE_DIRS            dist/ subdirectories cached for a year, default "assets/fonts vendor"
#   ALLOW_MOCK_SAMPLES        set to 1 to publish even if landing samples are missing or mock
set -euo pipefail

usage() { sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; }

MODE=deploy
case "${1:-}" in
  "") ;;
  --changeset-only) MODE=changeset ;;
  --site-only) MODE=site ;;
  -h | --help) usage; exit 0 ;;
  *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Git Bash rewrites arguments that look like POSIX paths before handing them to aws.exe
# ("/*" would become "C:/Program Files/Git/*"). Switch that off; every file argument below
# is relative to the repo root instead.
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

REGION=us-east-1
PROFILE="${AWS_PROFILE:-plainly-agent}"
APP_NAME="${APP_NAME:-plainly}"
STACK_NAME="${STACK_NAME:-$APP_NAME}"
TEMPLATE=infra/template.yaml

log() { printf '\n==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

if command -v aws >/dev/null 2>&1; then
  AWS_BIN=aws
elif [[ -x "/c/Program Files/Amazon/AWSCLIV2/aws.exe" ]]; then
  AWS_BIN="/c/Program Files/Amazon/AWSCLIV2/aws.exe"
else
  die "AWS CLI v2 not found on PATH or in C:\\Program Files\\Amazon\\AWSCLIV2"
fi

if [[ -n "${PYTHON:-}" ]]; then
  PY="$PYTHON"
elif command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

aws_() { "$AWS_BIN" --profile "$PROFILE" --region "$REGION" "$@"; }
# Text output without the CR that aws.exe and Windows Python put on every line.
aws_text() { aws_ "$@" --output text | tr -d '\r'; }
py_out() { "$PY" "$@" | tr -d '\r'; }

# ------------------------------------------------------------------ checks

check_function_in_sync() {
  "$PY" - <<'EOF'
import sys

def code_lines(text):
    lines = (line.strip() for line in text.splitlines())
    return [line for line in lines if line and not line.startswith("//")]

source = open("infra/cf-function.js", encoding="utf-8").read()
template = open("infra/template.yaml", encoding="utf-8").read().splitlines()
start = next(i for i, line in enumerate(template) if line.strip() == "FunctionCode: |")
indent = len(template[start]) - len(template[start].lstrip())
block = []
for line in template[start + 1:]:
    if line.strip() and len(line) - len(line.lstrip()) <= indent:
        break
    block.append(line)
if code_lines(source) != code_lines("\n".join(block)):
    sys.exit("error: infra/cf-function.js and FunctionCode in infra/template.yaml differ; make them match.")
EOF
}

lint_template() {
  if ! "$PY" -c "import cfnlint" >/dev/null 2>&1; then
    log "cfn-lint not installed; skipping template lint (pip install cfn-lint)"
    return
  fi
  local rc=0
  "$PY" -c "import sys; from cfnlint.runner import main; sys.exit(main())" "$TEMPLATE" || rc=$?
  # cfn-lint exit code is a bit mask: 2 = errors, 4 = warnings, 8 = informational.
  (( rc & 2 )) && die "cfn-lint reported errors in $TEMPLATE"
  return 0
}

resolve_account() {
  ACCOUNT_ID="$(aws_text sts get-caller-identity --query Account)" ||
    die "no credentials for profile $PROFILE; run: aws login --profile $PROFILE --region $REGION"
  log "Account $ACCOUNT_ID, profile $PROFILE, region $REGION, stack $STACK_NAME"
}

require_alert_email_for_create() {
  if [[ "$1" == NONE || "$1" == REVIEW_IN_PROGRESS ]] && [[ -z "${ALERT_EMAIL:-}" ]]; then
    die "stack $STACK_NAME does not exist yet; set ALERT_EMAIL for alarm and budget notifications"
  fi
}

stack_status() {
  aws_text cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --query 'Stacks[0].StackStatus' 2>/dev/null || echo NONE
}

# A failed first create leaves the stack in ROLLBACK_COMPLETE, which can only be deleted.
refuse_rolled_back_stack() {
  [[ "$1" == ROLLBACK_COMPLETE ]] || return 0
  die "stack $STACK_NAME is ROLLBACK_COMPLETE: its first create failed, and it can't be updated.
  1. Find the first failure:
       aws cloudformation describe-stack-events --stack-name $STACK_NAME \\
         --query \"StackEvents[?ResourceStatus=='CREATE_FAILED'].[LogicalResourceId,ResourceStatusReason]\"
  2. Fix the cause, then delete the stack from your own shell (DeleteStack is denied through the MCP server):
       aws cloudformation delete-stack --stack-name $STACK_NAME
       aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME
  3. Run this script again."
}

# ------------------------------------------------------------------ artifacts

ensure_artifacts_bucket() {
  ARTIFACTS="${APP_NAME}-artifacts-${ACCOUNT_ID}"
  if aws_ s3api head-bucket --bucket "$ARTIFACTS" >/dev/null 2>&1; then
    return
  fi
  log "Creating artifacts bucket $ARTIFACTS"
  aws_ s3api create-bucket --bucket "$ARTIFACTS" >/dev/null
  aws_ s3api wait bucket-exists --bucket "$ARTIFACTS"
  aws_ s3api put-public-access-block --bucket "$ARTIFACTS" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws_ s3api put-bucket-versioning --bucket "$ARTIFACTS" --versioning-configuration Status=Enabled
  aws_ s3api put-bucket-encryption --bucket "$ARTIFACTS" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws_ s3api put-bucket-lifecycle-configuration --bucket "$ARTIFACTS" --lifecycle-configuration \
    '{"Rules":[{"ID":"prune-old-versions","Status":"Enabled","Filter":{},
      "NoncurrentVersionExpiration":{"NoncurrentDays":30},
      "AbortIncompleteMultipartUpload":{"DaysAfterInitiation":7}}]}'
}

upload_lambda() {
  local zip
  zip="$(py_out scripts/package_lambda.py)"
  CODE_KEY="lambda/$(basename "$zip")"
  if aws_ s3api head-object --bucket "$ARTIFACTS" --key "$CODE_KEY" >/dev/null 2>&1; then
    log "Lambda package $CODE_KEY already uploaded"
  else
    log "Uploading $zip to s3://$ARTIFACTS/$CODE_KEY"
    aws_ s3 cp "$zip" "s3://$ARTIFACTS/$CODE_KEY" --only-show-errors
  fi
}

# Template parameters as KEY=VALUE words, only for values we actually know.
collect_parameters() {
  PARAMS=(AppName="$APP_NAME" CodeBucket="$ARTIFACTS" CodeKey="$CODE_KEY")
  PARAMS+=(PermissionsBoundaryArn="${PERMISSIONS_BOUNDARY_ARN-arn:aws:iam::${ACCOUNT_ID}:policy/plainly-boundary}")
  local pair
  for pair in AlertEmail:ALERT_EMAIL ModelIds:MODEL_IDS DailyCap:DAILY_CAP \
              RateLimitPerHour:RATE_LIMIT_PER_HOUR LogLevel:LOG_LEVEL MonthlyBudgetUsd:MONTHLY_BUDGET_USD; do
    local key="${pair%%:*}" var="${pair#*:}"
    if [[ -n "${!var:-}" ]]; then
      PARAMS+=("$key=${!var}")
    fi
  done
}

# The two NoEcho secrets (see the template). Random on first create; afterwards they are left out, so
# CloudFormation keeps the previous values. Nothing here prints them.
add_secret_parameters() {
  local status="$1" pair key var known
  for pair in OriginVerifySecret:ORIGIN_VERIFY_SECRET IpHashSalt:IP_HASH_SALT; do
    key="${pair%%:*}" var="${pair#*:}"
    if [[ -n "${!var:-}" ]]; then
      PARAMS+=("$key=${!var}")
      continue
    fi
    known=""
    if [[ "$status" != NONE && "$status" != REVIEW_IN_PROGRESS ]]; then
      known="$(aws_text cloudformation describe-stacks --stack-name "$STACK_NAME" \
        --query "Stacks[0].Parameters[?ParameterKey=='$key'].ParameterKey")"
    fi
    if [[ -z "$known" || "$known" == None ]]; then
      log "Generating a random $key"
      PARAMS+=("$key=$(py_out -c 'import secrets; print(secrets.token_hex(32))')")
    fi
  done
}

# ------------------------------------------------------------------ stack

deploy_stack() {
  local role_args=()
  if [[ -n "${CFN_ROLE_ARN:-}" ]]; then role_args=(--role-arn "$CFN_ROLE_ARN"); fi

  log "Deploying stack $STACK_NAME"
  aws_ cloudformation deploy \
    --stack-name "$STACK_NAME" \
    --template-file "$TEMPLATE" \
    --s3-bucket "$ARTIFACTS" --s3-prefix templates \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset \
    --parameter-overrides "${PARAMS[@]}" \
    --tags app="$APP_NAME" project=zero-to-shipped \
    ${role_args[@]+"${role_args[@]}"}
}

create_change_set() {
  local status="$1" type=UPDATE
  if [[ "$status" == NONE || "$status" == REVIEW_IN_PROGRESS ]]; then type=CREATE; fi

  local digest template_key template_url params_file=build/changeset-params.json
  digest="$(py_out -c "import hashlib; print(hashlib.sha256(open('$TEMPLATE','rb').read()).hexdigest()[:12])")"
  template_key="templates/template-$digest.yaml"
  aws_ s3 cp "$TEMPLATE" "s3://$ARTIFACTS/$template_key" --only-show-errors
  template_url="https://$ARTIFACTS.s3.$REGION.amazonaws.com/$template_key"

  # On UPDATE, every parameter we do not set keeps its current value instead of the default.
  mkdir -p build
  "$PY" - "$type" "${PARAMS[@]}" >"$params_file" <<'EOF'
import json, re, sys

kind, given = sys.argv[1], dict(arg.split("=", 1) for arg in sys.argv[2:])
template = open("infra/template.yaml", encoding="utf-8").read()
section = re.search(r"^Parameters:\n(.*?)^\S", template, re.S | re.M).group(1)
declared = re.findall(r"^  (\w+):\s*$", section, re.M)
params = [{"ParameterKey": k, "ParameterValue": v} for k, v in given.items()]
if kind == "UPDATE":
    params += [{"ParameterKey": k, "UsePreviousValue": True} for k in declared if k not in given]
json.dump(params, sys.stdout, indent=2)
EOF

  local name role_args=()
  name="${STACK_NAME}-$(date -u +%Y%m%d-%H%M%S)"
  if [[ -n "${CFN_ROLE_ARN:-}" ]]; then role_args=(--role-arn "$CFN_ROLE_ARN"); fi

  log "Creating $type change set $name"
  # This runs as an `if` condition, so set -e is off in here: every step that can fail is checked.
  CHANGE_SET_ARN="$(aws_text cloudformation create-change-set \
    --stack-name "$STACK_NAME" \
    --change-set-name "$name" \
    --change-set-type "$type" \
    --template-url "$template_url" \
    --parameters "file://$params_file" \
    --capabilities CAPABILITY_NAMED_IAM \
    --tags Key=app,Value="$APP_NAME" Key=project,Value=zero-to-shipped \
    ${role_args[@]+"${role_args[@]}"} \
    --query Id)" || { rm -f "$params_file"; die "create-change-set failed (see the error above)"; }
  rm -f "$params_file"  # it may hold the generated secrets
  [[ -n "$CHANGE_SET_ARN" ]] || die "create-change-set returned no change set id"

  if ! aws_ cloudformation wait change-set-create-complete --change-set-name "$CHANGE_SET_ARN" 2>/dev/null; then
    local reason
    reason="$(aws_text cloudformation describe-change-set --change-set-name "$CHANGE_SET_ARN" --query StatusReason)"
    if [[ "$reason" == *"didn't contain changes"* || "$reason" == *"No updates are to be performed"* ]]; then
      aws_ cloudformation delete-change-set --change-set-name "$CHANGE_SET_ARN"
      log "No infrastructure changes; the stack already matches. Nothing to execute."
      return 1
    fi
    die "change set failed: $reason"
  fi

  aws_ cloudformation describe-change-set --change-set-name "$CHANGE_SET_ARN" \
    --query 'Changes[].ResourceChange.{Action:Action,Resource:LogicalResourceId,Type:ResourceType,Replace:Replacement}' \
    --output table >&2
}

# ------------------------------------------------------------------ site

read_outputs() {
  local outputs
  outputs="$(aws_text cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]')" || die "stack $STACK_NAME not found"
  output() { awk -F'\t' -v k="$1" '$1 == k { print $2 }' <<<"$outputs"; }
  SITE_URL="$(output SiteUrl)"
  SITE_BUCKET="$(output SiteBucket)"
  DISTRIBUTION_ID="$(output DistributionId)"
  DASHBOARD_URL="$(output DashboardUrl)"
  [[ -n "$SITE_BUCKET" && -n "$DISTRIBUTION_ID" ]] || die "stack $STACK_NAME has no site outputs yet"
}

# Content types are set explicitly: on Windows the CLI guesses them from the registry and can
# label .js as text/plain, which browsers then refuse to run under X-Content-Type-Options: nosniff.
CONTENT_TYPES=(
  "html|text/html; charset=utf-8"      "css|text/css; charset=utf-8"
  "js|text/javascript; charset=utf-8"  "mjs|text/javascript; charset=utf-8"
  "json|application/json; charset=utf-8" "map|application/json"
  "webmanifest|application/manifest+json" "xml|application/xml"
  "txt|text/plain; charset=utf-8"      "ics|text/calendar; charset=utf-8"
  "svg|image/svg+xml"  "png|image/png"  "jpg|image/jpeg"  "jpeg|image/jpeg"  "webp|image/webp"
  "avif|image/avif"    "gif|image/gif"  "ico|image/x-icon"
  "woff2|font/woff2"   "woff|font/woff" "ttf|font/ttf"    "otf|font/otf"
  "mp4|video/mp4"      "webm|video/webm" "vtt|text/vtt; charset=utf-8"
  "pdf|application/pdf" "wasm|application/wasm"
)
IMMUTABLE="public, max-age=31536000, immutable"
SHORT="public, max-age=3600"
# Directories under dist/ whose files never change under the same name get a one-year cache.
# assets/app.js and assets/style.css are not fingerprinted, so they stay on SHORT; add "assets"
# here (or via the IMMUTABLE_DIRS env var) once build_site.py hashes or versions asset URLs.
read -r -a IMMUTABLE_DIRS <<<"${IMMUTABLE_DIRS-assets/fonts vendor}"

has_files() { [[ -n "$(find "$@" -type f -print -quit 2>/dev/null)" ]]; }

sync_group() {
  local include="$1" type="$2" cache="$3"; shift 3
  aws_ s3 sync dist/ "s3://$SITE_BUCKET/" --only-show-errors \
    --exclude "*" --include "$include" "$@" --content-type "$type" --cache-control "$cache"
}

publish_site() {
  read_outputs
  [[ -f scripts/build_site.py ]] || die "scripts/build_site.py is missing"
  log "Building site into dist/"
  # --strict refuses to publish landing samples that are missing or still mock data.
  # ALLOW_MOCK_SAMPLES=1 skips that, e.g. for a first infrastructure test before the live sample run.
  local strict=(--strict)
  [[ "${ALLOW_MOCK_SAMPLES:-}" == 1 ]] && strict=()
  SITE_URL="$SITE_URL" "$PY" scripts/build_site.py ${strict[@]+"${strict[@]}"}
  [[ -f dist/index.html ]] || die "scripts/build_site.py did not produce dist/index.html"

  log "Uploading dist/ to s3://$SITE_BUCKET"
  local entry ext type fresh dir excludes prune
  for entry in "${CONTENT_TYPES[@]}"; do
    ext="${entry%%|*}" type="${entry#*|}"
    case "$ext" in html | json | webmanifest | xml | txt | ics) fresh="no-cache" ;; *) fresh="$SHORT" ;; esac
    excludes=() prune=()
    for dir in ${IMMUTABLE_DIRS[@]+"${IMMUTABLE_DIRS[@]}"}; do
      excludes+=(--exclude "$dir/*")
      prune+=(-path "dist/$dir" -prune -o)
      if has_files "dist/$dir" -name "*.$ext"; then
        sync_group "$dir/*.$ext" "$type" "$IMMUTABLE"
      fi
    done
    if has_files dist ${prune[@]+"${prune[@]}"} -name "*.$ext"; then
      sync_group "*.$ext" "$type" "$fresh" ${excludes[@]+"${excludes[@]}"}
    fi
  done
  # Anything not covered above (guessed type), then prune objects no longer in dist/.
  aws_ s3 sync dist/ "s3://$SITE_BUCKET/" --only-show-errors --delete --cache-control "$SHORT"

  log "Invalidating CloudFront cache"
  local invalidation
  invalidation="$(aws_text cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" --query Invalidation.Id)"
  log "Invalidation $invalidation submitted (usually done within a minute or two)"

  if command -v curl >/dev/null 2>&1; then
    if curl -fsS -m 20 "$SITE_URL/api/health" >/dev/null; then
      log "Health check OK: $SITE_URL/api/health"
    else
      log "Health check failed: $SITE_URL/api/health (see the dashboard and /aws/lambda/$APP_NAME-api logs)"
    fi
  fi
}

# ------------------------------------------------------------------ main

check_function_in_sync

case "$MODE" in
  site)
    publish_site
    ;;
  changeset)
    lint_template
    resolve_account
    STATUS="$(stack_status)"
    refuse_rolled_back_stack "$STATUS"
    require_alert_email_for_create "$STATUS"
    ensure_artifacts_bucket
    upload_lambda
    collect_parameters
    add_secret_parameters "$STATUS"
    if create_change_set "$STATUS"; then
      log "Change set ready and NOT executed. Execute it (e.g. through the AWS MCP server) with:
    aws cloudformation execute-change-set --change-set-name $CHANGE_SET_ARN
then wait for the stack, and publish the site with: scripts/deploy.sh --site-only"
      echo "$CHANGE_SET_ARN"
    fi
    exit 0
    ;;
  deploy)
    lint_template
    resolve_account
    STATUS="$(stack_status)"
    refuse_rolled_back_stack "$STATUS"
    require_alert_email_for_create "$STATUS"
    ensure_artifacts_bucket
    upload_lambda
    collect_parameters
    add_secret_parameters "$STATUS"
    deploy_stack
    publish_site
    ;;
esac

log "Dashboard: $DASHBOARD_URL"
printf '\nSiteUrl: %s\n' "$SITE_URL"
