**Research: "connect your coding agent to the AWS console", proof of connection, and a cheap setup for Zero to Shipped (as of 2026-09-30)**

Tags: [V] means I saw it on the cited page. [I] means it is my inference.

Short answer: Claude Code counts, and nothing in the official material favours Kiro or Q. The most literal way to "connect to the AWS console" is AWS's Agent Toolkit flow: Console Home → Agent Toolkit banner → "Get setup prompt", or its CLI equivalent `aws login` + `aws configure agent-toolkit`. That connects Claude Code to the managed AWS MCP Server. The rules don't define a proof format, so the strongest proof stacks screenshots, the `/mcp` connection status, a session transcript and CloudTrail records.

---

### 1. Official sources and what they say

**Hackathon page** (https://builder.aws.com/build/hackathons/e83e84e5-4f4c-383b-bbe9-4a15ac195d55/zero-to-shipped)
- The site is a single-page app. The rules are embedded in the page's server-rendered JSON and only come back for crawler user-agents such as `facebookexternalhit`; a plain fetch returns an empty shell.
- [V] 3,379 participants registered (the brief said about 2,900).
- [V] `hackathonType: "BUILD_OWN_ACCOUNT"`.
- [V] Judges, by alias: bhavinjp, karamen, raghuramg, manubel, hamzalfa.
- [V] Sponsors: "-", so there are none. The Terms say "The Hackathon is sponsored by AWS."
- [V] Tags: one category tag (#workplace-efficiency, #daily-life-enhancement, #commercial-potential, #social-good or #personal-expression) and one lane tag. The official lane tag is **#startups** (plural) or **#community**.
- [V] Social Good entries may qualify to apply for AWS Social Impact Credits (https://pulse.amazon/application/9XSD9BPP?source=zerotoshipped2026).
- [V] Timeline:
  - Gate 1: week of Oct 5
  - Gate 2: week of Oct 12
  - Winners: week of Oct 19

**Official Terms, same page, "Rules" tab (Last Updated Sep 18, 2026). These govern.**
- [V] What a submission must include: "(1) a live, publicly reachable application running on AWS, (2) documented proof of coding agent connection to the AWS console, (3) a published project on AWS Builder Center describing the application, development process, and how the coding agent was used, and (4) designation of one of five app categories and a focus track."
- [V] You must also:
  - "Connect a coding agent to the AWS console before or during the Submission Period"
  - "Document their use of AWS services and coding agent in their submission"
- [V] Ship gate: "live on AWS and reachable via a public URL at the time of evaluation", "Include documented proof of coding agent connection", "Accessible to both the AI scoring system and human judges". It is pass/fail "with no exceptions".
- [V] **The rubric has four equally weighted criteria, used at both gates:**
  - Technical Innovation & Originality (25%)
  - Implementation Quality (25%)
  - Community/Market Impact (25%)
  - Creativity & Storytelling (25%)
- [V] Gate 1 is "a combination of AI and Human review". The top 100 advance. Gate 2 is "A panel of AWS experts and community leaders", which picks 5 winners "across the app categories".
- [V] **This conflicts with the About tab.** About says Round 1 is AI-only and lists "communication quality" instead of "Implementation Quality". [I] Treat the Terms as authoritative.
- [V] Excluded countries: Argentina, Australia, Brazil, Hong Kong, Indonesia, Italy, the Philippines, Vietnam, Singapore, Russia, Cuba, Iran, North Korea, Syria, Belarus, Crimea/DNR/LNR and the UAE. India is not on the list. Amazon employees and their families are excluded. One entry per person.
- [V] Finalists may be checked against LinkedIn.
- [V] Credits arrive "within 30 days of winner announcement".
- [V] Free Tier note: "To the extent that a participant enters ... using an AWS account under the AWS Free Tier, the AWS Free Tier Terms will apply... an AWS Free Tier account will not automatically convert to a paid account." No hackathon credits are given to participants.
- [V] Winners may be showcased "at re:Invent 2026".

**"Introducing Hackathons on AWS Builder Center"** (Rick Suttles, Director, AWS Builder Center; Sep 18, 2026) — https://builder.aws.com/content/3JVlS5EVmqlZEcNMWMNeJhln9Sp/introducing-hackathons-on-aws-builder-center
- [V] Project fields:
  - title: up to 255 characters
  - **description: up to 512 characters**
  - body: rich text
  - links: GitHub/GitLab repo, "endpoint or live demo", notebook
  - cover image
  - **up to five tags**
- [V] "Publishing is submitting." Projects stay editable until the end date, but "A draft left unpublished when the hackathon ends cannot be published afterwards and cannot win an award. **Publish early and keep editing.**" Solo entries are allowed.
- [I] Two tags are required, which leaves three free tag slots.

**The "launch article" URL in the brief is not official.** https://builder.aws.com/content/3JjizKCGyDjqLHiUnaEXmSdi3aE/... was posted by community member Muhammad Saadullah on Sep 23. [V] It has a disclaimer and a `utm_source=gemini` link. [I] It is probably AI-assisted. It gives "GitHub Copilot, Amazon Q, Claude, or Cursor" as example agents and says to "capture screenshots or logs of the integration". It also uses "#startup", which is wrong. Use it for colour only.

**AWS Weekly Roundup, Sep 21, 2026** (Esra Kayabali) — https://aws.amazon.com/blogs/aws/aws-weekly-roundup-aws-builder-center-mobile-apps-amazon-connect-talent-ga-amazon-corretto-27-and-more-september-14-2026/
- [V] "You connect your coding agent to AWS, build a real application, and ship it live on AWS."

### 2. The judges (public Builder Center profiles, all tagged "AWS Employee")
- bhavinjp: Bhavin Patel, AWS Startups Solutions Architect, IL. Helps "early-stage startups ... path from idea to production". https://builder.aws.com/community/@bhavinjp
- karamen: Abdullah Karaman, Technical Account Manager at AWS. https://builder.aws.com/community/@karamen
- raghuramg: Raghuram, Senior SA "supporting engaged AI/ML startups in SF", 20+ years (eBay, Intuit, Oracle, Salesforce, Walmart). https://builder.aws.com/community/@raghuramg
- manubel: Manuela, Solutions Architect / DevOps engineer, Netherlands; "DevOps, automations, cloud operations and security". https://builder.aws.com/community/@manubel
- hamzalfa: Hamza Alfarrash, Cloud Consultant, Canada; "helping enterprises modernize". https://builder.aws.com/community/@hamzalfa

[I] Two of the five are startup SAs. The panel will likely reward sound, secure, least-privilege serverless architecture and a credible product story. The Terms add "community leaders" at Gate 2, so the panel may be larger than these five.

### 3. What "connect your coding agent to the AWS console" most likely means
- [V] AWS Developer Advocate Ana Cunha published **"Connect your AI coding agent to AWS"** on Sep 17, 2026, the day before launch. https://builder.aws.com/content/3JQdUYne1ujIvtoLgWiV7iBGklF/connect-your-ai-coding-agent-to-aws
  - Easiest path: "Sign in to the AWS Console. At the top of Console Home, you'll see the Agent Toolkit for AWS banner. Click Get setup prompt, then paste the prompt into your coding agent's chat." The agent then "installs the AWS CLI..., signs you in with aws login, connects to the AWS MCP Server, and installs the core AWS skills."
  - Manual path: CLI 2.35.0 or later, then `aws login`, then `aws configure agent-toolkit`, then restart the agent.
  - Check: ask "What AWS Regions are available?"
  - "It works with the agent you already use: Kiro, Claude Code, Codex, Cursor."
  - "The Agent Toolkit is free."
- [I] The hackathon page never links this article. Its timing, its wording ("connect your AI coding agent to AWS") and the Console Home banner make it the most likely intended mechanism. It also matches the rule's "AWS console" wording literally.
- [V] **Agent Toolkit for AWS.** Launched May 6, 2026 (https://aws.amazon.com/about-aws/whats-new/2026/05/agent-toolkit/). `aws configure agent-toolkit` was added to the CLI on Jun 5, 2026 (https://aws.amazon.com/about-aws/whats-new/2026/06/aws-cli-agent-toolkit/).
  - It has four parts: the AWS MCP Server, skills, plugins for Claude Code and Codex, and rules files.
  - "no additional charge".
  - Source: https://docs.aws.amazon.com/agent-toolkit/latest/userguide/what-is-agent-toolkit.html
- [V] **AWS MCP Server endpoints:** `https://aws-mcp.us-east-1.api.aws/mcp` and eu-central-1. It supersedes aws-api-mcp-server and aws-knowledge-mcp-server; remove those to avoid conflicting tools. https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html
- [V] **Claude Code has three documented ways to connect:**
  - OAuth: `claude mcp add aws-mcp https://aws-mcp.us-east-1.api.aws/mcp --transport http`. The IAM principal needs `AWSMCPSignInOAuthAccessPolicy`. Tokens last 1 hour and refresh for up to 12 hours.
  - SigV4, which the docs recommend for terminal agents like Claude Code: `aws login`, then `claude mcp add-json aws-mcp '{"type":"stdio","command":"uvx","args":["mcp-proxy-for-aws-cli@latest","https://aws-mcp.us-east-1.api.aws/mcp","--metadata","AWS_REGION=us-east-1"],"env":{}}'`
  - Plugin: `/plugin install aws-core@claude-plugins-official` (https://github.com/aws/agent-toolkit-for-aws)
- [V] The OAuth flow for AWS MCP was announced Jul 9, 2026 and demonstrated with Claude Code. https://aws.amazon.com/blogs/security/introducing-oauth-support-for-aws-mcp-server/
- [V] **`aws login`** (CLI 2.32.0 or later, announced Nov 2025) uses your Management Console sign-in through a browser flow. It works with root, IAM user or federated identities.
  - Non-root users need `SignInLocalDevelopmentAccess`.
  - Credentials refresh every 15 minutes, for sessions of up to 12 hours.
  - Credentials are cached in `%USERPROFILE%\.aws\login\cache`.
  - Sign out with `aws logout`.
  - Sources: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html and https://aws.amazon.com/about-aws/whats-new/2025/11/console-credentials-aws-cli-sdk-authentication/
- [V] Checked locally: `aws-cli/2.37.6`, so `aws login` and `aws configure agent-toolkit` are both supported. `claude.exe` and `uvx.exe` are on PATH.
- [V] The setup instructions say "The Agent Toolkit service is currently only available in us-east-1". Verify with `aws agent-toolkit list-available-skills --region us-east-1`. https://github.com/aws/agent-toolkit-for-aws/blob/main/setup-instructions/setup.md
- [V] Amazon Q Developer CLI became Kiro CLI in November 2025. New Q Developer signups were blocked from May 15, 2026. https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/upgrade-to-kiro.html and https://aws.amazon.com/blogs/devops/amazon-q-developer-end-of-support-announcement/

### 4. Does Claude Code count? Is there a Kiro/Q preference?
- [V] The rules say "a coding agent" and never name a product. The About page says "your coding agent". The Agent Toolkit docs, Ana Cunha's article and the product page all list Claude Code as supported (https://aws.amazon.com/products/developer-tools/agent-toolkit-for-aws/).
- [V] I found no bonus, criterion or wording that favours Kiro or Q anywhere in the Terms or on the About page.
- [I] Any preference would be informal at most. The AWS-native part that matters is using the AWS MCP Server / Agent Toolkit, which works with Claude Code. Using `aws-core` skills also gives an "AWS best practices" story for Implementation Quality.

### 5. What proof format is expected
- [V] The official pages don't specify one. They only say "documented proof of coding agent connection to the AWS console", included in the Builder Center project.
- [V] The unofficial community article suggests "screenshots or logs".
- [V] Participant repos use `aws sts get-caller-identity` output (https://github.com/thirumaleshp/zero-to-shipped) or just screenshots and logs (https://github.com/Akash-Raj-Official/AWS-Zero-to-Shipped). I could not read the in-platform Projects or Discussion tabs, which load client-side.
- [V] **CloudTrail as evidence:**
  - AWS MCP tool calls are logged as `eventSource: aws-mcp.amazonaws.com`, `eventName: CallReadWriteTool`, `eventCategory: "Data"`, with an `mcpEventDetails.mcpServerName` field. https://docs.aws.amazon.com/agent-toolkit/latest/userguide/logging-using-cloudtrail.html
  - OAuth adds sign-in events `AuthorizeOAuth2Access` and `CreateOAuth2Token`.
  - The IAM context keys `aws:ViaAWSMCPService` and `aws:CalledViaAWSMCP` mark MCP-originated calls. https://aws.amazon.com/blogs/security/understanding-iam-for-managed-aws-mcp-servers/
  - A third-party blog says downstream calls show `invokedBy`/`sourceIPAddress`/`userAgent` = `aws-mcp.amazonaws.com`, and that MCP events are data events, so they need a trail with data events enabled (Event history only shows management events). https://hidekazu-konishi.com/entry/agent_toolkit_for_aws_and_the_aws_mcp_server.html. I have not confirmed this on an AWS page.
  - I could not find the exact `resources.type` value for an advanced data-event selector for aws-mcp. Check it in the console's data-event dropdown rather than guessing.

**[I] Recommended proof stack:**
1. Screenshot Console Home with the Agent Toolkit banner, then "Get setup prompt". This matches the literal "AWS console" wording.
2. Screenshot `aws login` in the terminal next to the browser consent page, then `aws sts get-caller-identity`. Partially mask the account ID.
3. Screenshot `aws configure agent-toolkit` output, or the `claude mcp add` command. Then Claude Code's `/mcp` showing `aws-mcp` connected, plus the "What AWS Regions are available?" answer.
4. Before building, create a trail with data events for the AWS MCP Server. After building, screenshot CloudTrail entries for `CallReadWriteTool` and for resources the agent created, such as `CreateFunction` and `CreateDistribution`, ideally showing `aws-mcp.amazonaws.com`.
5. A 60 to 90 second screen recording: prompt → agent calls an AWS tool → resource appears in the console → live URL.
6. In the repo: `docs/agent-log.md` with excerpts from the Claude Code transcript, the setup prompt, and a table of "what the agent did / what I did". Git commits with agent co-author trailers.
7. On the Builder Center post: a text section titled "Agent connection proof" with the images embedded, so both humans and the AI scorer can read it.

### 6. Spending, Free Tier, and the safest cheap architecture
- [V] The new Free Tier (July 2025) gives $100 of credits on signup and up to $100 more for activities. Two of those activities are "using Amazon Bedrock" and "setting up an AWS Budget". The free plan lasts 6 months or until credits run out. https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/
- [V] Bedrock serverless models have been auto-enabled since Sep 29, 2025, with no Model Access page. Anthropic models still need a one-time form. https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/
- [V] Third-party pricing, not confirmed on the AWS pricing page (which didn't render):
  - Nova Lite: $0.06 / $0.24 per 1M input/output tokens
  - Nova 2 Lite: $0.30 / $2.50 per 1M input/output tokens
  - Source: https://pricepertoken.com/pricing-page/model/amazon-nova-2-lite-v1
- [I] Plainly's current stack is the right one. Suggested shape and guardrails:
  - Hosting: private S3 bucket + CloudFront with Origin Access Control for the static site. Put the Lambda (Python) behind CloudFront or an API Gateway HTTP API rather than a bare `AuthType NONE` Function URL.
  - Model: Bedrock Converse with Nova Lite or Nova 2 Lite in us-east-1.
  - Storage: DynamoDB on-demand with a TTL. S3 lifecycle rule deleting uploads after 24 hours, which also helps the privacy story.
  - Guardrails:
    - Lambda reserved concurrency of about 5
    - image size cap
    - per-IP rate limit in DynamoDB
    - AWS Budget alert at $5–10
  - Expected cost is well under $5.
  - A least-privilege IAM role for the agent, plus an explicit deny on deletes via `aws:ViaAWSMCPService`, is a strong "Implementation Quality" and security point for this SA-heavy panel.
- [I] "Reachable by the AI scoring system": the landing page should render meaningful text without JavaScript (static HTML), have no WAF or CAPTCHA blocking bots, and include a sample letter so the demo works without uploads. Builder Center itself only serves content to some crawlers, which suggests the scorer may be crawler-based.

### 7. Things I could not find
- Any official FAQ or how-to linked from the hackathon page. The Resources and Discussion tabs are client-rendered and I didn't sign in.
- How the AI scorer works, or what model it uses.
- An organizer clarification of what counts as "proof".
- The exact CloudTrail data-event resource type for aws-mcp.
- Whether the Free Tier "free plan" restricts any services this stack needs.

### Action items for the next 2.5 days [I]
- Publish a draft Builder Center project today and keep editing it.
- Use #startups, not #startup.
- Write the 512-character description against the four equally weighted criteria.