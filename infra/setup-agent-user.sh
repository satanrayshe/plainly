#!/usr/bin/env bash
# One-time admin setup for the Plainly coding agent (run by Shrey, signed in as an administrator).
#   bash infra/setup-agent-user.sh                       # uses the CLI profile plainly-admin
#   ADMIN_PROFILE=<profile> bash infra/setup-agent-user.sh
#   YES=1 bash infra/setup-agent-user.sh                  # skip the "is this the right account?" prompt
# Creates: policies plainly-boundary + plainly-agent-policy, IAM user plainly-agent (console sign-in, no access keys),
# CloudFormation service role plainly-cfn-deploy, and API Gateway's service-linked role.
#
# Safe to run again: anything that already exists is left as it is and reported as "exists".
# An existing policy is never overwritten; if its document differs from the file here, the script
# says so and prints the command that would update it. The password is shown only when this run
# creates the console login.
#
# Works on the AWS Free account plan. It does not create an AWS Organization or anything else that
# would move the account to the Paid plan.
set -euo pipefail
export PATH="/c/Program Files/Amazon/AWSCLIV2:$PATH" MSYS_NO_PATHCONV=1
PROFILE="${ADMIN_PROFILE:-plainly-admin}"
aws() { command aws --profile "$PROFILE" --region us-east-1 "$@"; }
aws_text() { aws "$@" --output text | tr -d '\r'; }
cd "$(dirname "$0")/.."

if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1; then PY=python3; else PY=python; fi

created=() existing=() notes=()
step() { printf '\n-- %s\n' "$*"; }
made() { printf '   created: %s\n' "$1"; created+=("$1"); }
kept() { printf '   exists, left unchanged: %s\n' "$1"; existing+=("$1"); }

CALLER=$(aws_text sts get-caller-identity --query Arn)
ACCT=$(aws_text sts get-caller-identity --query Account)
echo "Profile $PROFILE -> account $ACCT as $CALLER"
if [[ -t 0 && "${YES:-}" != 1 ]]; then
  read -r -p "Is this Shrey's account? Continue [y/N] " answer
  [[ "$answer" == [yY]* ]] || { echo "Stopped; nothing was changed."; exit 1; }
fi

# Warn (never overwrite) when an existing managed policy differs from the JSON file.
compare_policy() {
  local arn="$1" file="$2" version live
  version=$(aws_text iam get-policy --policy-arn "$arn" --query Policy.DefaultVersionId)
  live=$(aws iam get-policy-version --policy-arn "$arn" --version-id "$version" \
    --query PolicyVersion.Document --output json | tr -d '\r')
  if LIVE="$live" "$PY" -c "import json,os,sys; sys.exit(json.loads(os.environ['LIVE']) != json.load(open(sys.argv[1], encoding='utf-8')))" "$file"; then
    printf '   matches %s\n' "$file"
  else
    printf '   NOTE: differs from %s. To update it (keeps at most 5 versions):\n' "$file"
    printf '     aws iam create-policy-version --policy-arn %s --policy-document file://%s --set-as-default\n' "$arn" "$file"
    notes+=("$arn differs from $file")
  fi
}

ensure_policy() {
  local name="$1" file="$2" arn="arn:aws:iam::$ACCT:policy/$1"
  step "Policy $name (from $file)"
  if aws iam get-policy --policy-arn "$arn" >/dev/null 2>&1; then
    kept "policy $name"
    compare_policy "$arn" "$file"
  else
    aws iam create-policy --policy-name "$name" --policy-document "file://$file" \
      --tags Key=project,Value=plainly >/dev/null
    made "policy $name"
  fi
}

ensure_policy plainly-boundary infra/plainly-boundary-policy.json
ensure_policy plainly-agent-policy infra/agent-iam-policy.json
AGENT_POLICY="arn:aws:iam::$ACCT:policy/plainly-agent-policy"

step "IAM user plainly-agent"
if aws iam get-user --user-name plainly-agent >/dev/null 2>&1; then
  kept "user plainly-agent"
else
  aws iam create-user --user-name plainly-agent --tags Key=project,Value=plainly >/dev/null
  made "user plainly-agent"
fi

# attach-user-policy / attach-role-policy succeed quietly when already attached.
attach_user() {
  local arn="$1"
  if [[ -n "$(aws_text iam list-attached-user-policies --user-name plainly-agent \
         --query "AttachedPolicies[?PolicyArn=='$arn'].PolicyArn")" ]]; then
    kept "user plainly-agent -> $(basename "$arn")"
  else
    aws iam attach-user-policy --user-name plainly-agent --policy-arn "$arn"
    made "user plainly-agent -> $(basename "$arn")"
  fi
}
attach_user "$AGENT_POLICY"
attach_user arn:aws:iam::aws:policy/SignInLocalDevelopmentAccess

step "Console sign-in for plainly-agent"
PW=""
new_password() {
  "$PY" -c "import secrets,string;a=string.ascii_letters+string.digits;print('Pl-'+''.join(secrets.choice(a) for _ in range(18))+'-9x')" | tr -d '\r'
}
if aws iam get-login-profile --user-name plainly-agent >/dev/null 2>&1; then
  if [[ "${RESET_PASSWORD:-}" == 1 ]]; then
    PW=$(new_password)
    aws iam update-login-profile --user-name plainly-agent --password "$PW" --no-password-reset-required >/dev/null
    made "new password for plainly-agent"
  else
    kept "console login for plainly-agent (password not shown; RESET_PASSWORD=1 sets a new one)"
  fi
else
  PW=$(new_password)
  aws iam create-login-profile --user-name plainly-agent --password "$PW" --no-password-reset-required >/dev/null
  made "console login for plainly-agent"
fi
if [[ -n "$PW" ]]; then
  printf '   user name: plainly-agent\n   password:  %s\n   sign-in:   https://%s.signin.aws.amazon.com/console\n' "$PW" "$ACCT"
fi

step "CloudFormation service role plainly-cfn-deploy"
if aws iam get-role --role-name plainly-cfn-deploy >/dev/null 2>&1; then
  kept "role plainly-cfn-deploy"
else
  # Relative path inside the repo: Windows aws.exe can't open Git Bash's /tmp.
  mkdir -p build
  TRUST=build/cfn-trust.json
  cat > "$TRUST" <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"cloudformation.amazonaws.com"},"Action":"sts:AssumeRole","Condition":{"StringEquals":{"aws:SourceAccount":"$ACCT"}}}]}
EOF
  aws iam create-role --role-name plainly-cfn-deploy --assume-role-policy-document "file://$TRUST" \
    --description "CloudFormation service role for the plainly stack" --tags Key=project,Value=plainly >/dev/null
  rm -f "$TRUST"
  made "role plainly-cfn-deploy"
fi
if [[ -n "$(aws_text iam list-attached-role-policies --role-name plainly-cfn-deploy \
       --query "AttachedPolicies[?PolicyArn=='$AGENT_POLICY'].PolicyArn")" ]]; then
  kept "role plainly-cfn-deploy -> plainly-agent-policy"
else
  aws iam attach-role-policy --role-name plainly-cfn-deploy --policy-arn "$AGENT_POLICY"
  made "role plainly-cfn-deploy -> plainly-agent-policy"
fi

step "API Gateway service-linked role"
if aws iam get-role --role-name AWSServiceRoleForAPIGateway >/dev/null 2>&1; then
  kept "role AWSServiceRoleForAPIGateway"
else
  aws iam create-service-linked-role --aws-service-name ops.apigateway.amazonaws.com >/dev/null
  made "role AWSServiceRoleForAPIGateway"
fi

printf '\n== Summary for account %s\n' "$ACCT"
printf '   created: %s\n' "${#created[@]}"
for item in ${created[@]+"${created[@]}"}; do printf '     + %s\n' "$item"; done
printf '   already there: %s\n' "${#existing[@]}"
for item in ${existing[@]+"${existing[@]}"}; do printf '     = %s\n' "$item"; done
for item in ${notes[@]+"${notes[@]}"}; do printf '   NOTE: %s\n' "$item"; done

cat <<EOF

CloudFormation service role for deploys:
  export CFN_ROLE_ARN=arn:aws:iam::$ACCT:role/plainly-cfn-deploy
EOF
if [[ -n "$PW" ]]; then
  cat <<EOF

Sign-in details for plainly-agent (shown once; keep them private):
  Sign-in URL: https://$ACCT.signin.aws.amazon.com/console
  User name:   plainly-agent
  Password:    $PW
EOF
fi
cat <<EOF

Next: aws login --region us-east-1 --profile plainly-agent
      aws sts get-caller-identity --profile plainly-agent    # Arn must end in :user/plainly-agent
Do NOT create an AWS Organization on a Free-plan account (it moves the account to the Paid plan);
see "Free plan" in infra/README-infra.md.
EOF
