# Zero to Shipped competitor map (as of 2026-09-30, about 2.5 days before the deadline)

## Bottom line
- The public project gallery has **150 submissions** out of 3,379 registered participants. I pulled all of them from the site's public submissions API: `https://api.builder.aws.com/cs/submissions/parent/e83e84e5-4f4c-383b-bbe9-4a15ac195d55?parentContentType=HACKATHON`. I found about 45 more entries in progress on GitHub. **VERIFIED**
- The most crowded space is **AI copilots for AWS cloud ops, FinOps, security and incidents**, at about 25–27% of the field. Three different projects are called "CloudPulse AI" and two are called "CloudGuard AI". The next most crowded is **study-notes to summary/flashcards/quiz tutors**.
- **The "explain confusing documents" space is not crowded but it is a stock idea.** About 4 of 150 submissions do it directly, with 1 more on GitHub. **None of the 150 submissions mentions scams, phishing or fraud.** None does photo of a letter → multilingual explanation → scam check → reply draft. **VERIFIED by keyword scan**
- The risk is being seen as generic. Another hackathon's builder called the "Document Explainer Agent" "idea #1 from the prompt list" (https://github.com/Satyasarathi-022/plainread).

## 1. Sources and method
| Source | Result |
|---|---|
| Hackathon page, Builder Center (https://builder.aws.com/build/hackathons/e83e84e5-4f4c-383b-bbe9-4a15ac195d55/zero-to-shipped) | **VERIFIED:** 3,379 participants, $28,000 pool, judge aliases bhavinjp, karamen, raghuramg, manubel, hamzalfa. **No sponsors listed.** Judging weights are not on the page. |
| Public submissions API (URL above) | **VERIFIED:** 150 projects, all status LIVE. Fields include title, description, tags, likes, live link and GitHub link. Project pages are `https://builder.aws.com/project/<id>`. |
| GitHub public search API (repos that mention "Zero to Shipped" in the README or description, created after Sep 10) | About 45 real Zero to Shipped entries, 17 of them not yet in the gallery. I excluded repos from two other hackathons (the WeMakeDevs "First Commit"/Bharat Builds hackathon and "Agents for Humans") and workshop repos with the same name. |
| Observable forum (https://talk.observablehq.com/t/zero-to-shipped/10885) | One project, veggie.farm. |
| dev.to, LinkedIn, Medium, Reddit searches | Nothing useful. The one dev.to post (Porch Light, https://dev.to/earlgreyhot1701d/block-zero-oh-no-claude-kiro-and-i-over-engineered-the-throwaway-5d42) doesn't name this hackathon. |
| Builder Center hackathon article topic page and Discussion tab | Couldn't read them. The topic page is script-rendered and the posts API returns `FEATURE_DISABLED`. |

Raw data is saved in the scratchpad: `...\scratchpad\comp\subs.json` (all 150 submissions) and `...\scratchpad\readmes.json` (GitHub READMEs).

## 2. Field statistics (VERIFIED from the API)
- **Category tags** (a project can have more than one): social-good 24, commercial-potential 20, workplace-efficiency 17, daily-life-enhancement 11, personal-expression 5.
- **Lane tags:** startups 35, community 24.
- **Missing tags:** 81 of 150 have no category tag and 91 have no lane tag. The rules say every entry needs both. **INFERRED:** about half the field may fail the requirements or score low.
- **Live links:**
  - 71 point to AWS domains (amplifyapp, cloudfront, execute-api, lambda-url, awsapprunner).
  - 26 point to clearly non-AWS hosts (Vercel, Render, github.io, Streamlit, YouTube, Google Drive, even a claude.ai artifact).
  - 35 have no link.
  - 18 use custom domains whose hosting I couldn't tell.
- **Pace:** about 10–17 new submissions a day. Likes are low (maximum 4), so community voting is not a real factor.
- **Coding agents named in write-ups:** MCP 30, Claude Code 18, Kiro 14, Gemini 13, Codex 10, Copilot 8, Antigravity 8, Amazon Q 6.

## 3. Catalog by cluster
The cluster assignments are my own reading, so they are **INFERRED**. Each project's existence and description is **VERIFIED** from the API or its repo. [GH] means it's on GitHub but not yet in the gallery.

**A. AWS cloud ops, FinOps, security, DevOps tools (~40, the most crowded)**
- OpsPulse AI: incident triage plus FinOps, Claude on Bedrock, Amplify.
- CloudPulse AI ×3: SamiSiddiqui45 (FinOps and Well-Architected), Shiva-Matangulu (zombie resources), pawaraditya0903 (SRE copilot).
- CloudGuard AI: security posture checks (CSPM), CloudFront.
- CloudLens: architecture intelligence SaaS with Bedrock Knowledge Bases.
- AgentSentry: CloudWatch alarm → pull request with a fix, built with Kiro.
- CloudRescue AI, AegisOps AI, PingsNest, FaultLine, DiffPulse, Nimbo, zombiescan.
- PostMortem AI: Bedrock plus Lambda Function URL.
- Mini-SOC, TF StateCraft, BlastRadius, Firsthand, HookRelay, DeepPR, Mitigateit, ReleaseGuard AI, Specloom, IssueWorth, AI-DLC Learning Simulator, Agent Trail, Once, QueryAI, Flowent, podex, DocprescOps.
- Plain infrastructure write-ups: 3-tier app, 4-tier app, EKS workstation.
- [GH] CloudSentinel AI, CloudAgent AI, vedanshg7572's CloudGuard AI, Threefold, AgentAudit.

**B. Education and study (~24)**
- Misconception Map, StudySnap, PadhAI/ExamSaathi. PadhAI takes a photo of a textbook page and explains it in plain Hindi or English, which is the same interaction as Plainly.
- NotesForAll, studypilot, LEGACY, SmartMov, CloudCard, CodeArena, CodeWithMe, CyberLearn AI, Class Complexity AI, LabSim Coach, ByteGeist Support Lab, Magnus, Deadline Agent, StudyTrack, PeerLearn, AYNI Twin, Ouvido Musical, CampusOne, Arth, HandoverOS.
- EduLens: college rules into plain English (also listed under cluster F).
- [GH] RojLearn, AI Student Cloud.

**C. Career and hiring (~6–8)**
- InterviewCoach AI, SkillGraph, Skillora, Resume-matcher, CapXAI, CareerG1.
- [GH] SkillBridge AI ×2.

**D. Climate, disaster, civic, safety (~21)**
- Floods alone are a mini-cluster: Accra Flood Watch, AquaTrace, MazhaiMunnadi, and [GH] NeerVazhi.
- Civic reporting: Rapport (New Orleans 311 reports), MtaaFix.
- Emergency and warnings: RescueOps, ResiliNet, AvisoAndino (weather alerts by SMS), Calltree (phones elderly people during heat warnings), ShiftGuard.
- Other: SecondBreath, GeoGuard, NER logistics, zoop, SentiAI, SafePulse, Border-Sense, driver drowsiness detection ×2, railway block planner, HarvestAI.

**E. Health (~3)**
- RuralDiag, Medicine Support Hub, BillShield. [GH] AccessAI Agent.

**F. Document and plain-language explainers (Plainly's space)**
| Project | What it does | Threat to Plainly |
|---|---|---|
| OBLIGRA (https://builder.aws.com/project/3JcsNaFfrvpOVQKkudq78xm61I3) | Takes PDFs, screenshots and notices and extracts obligations, deadlines, dependencies and risks. Live on CloudFront. Workplace category. | **Highest overlap** with Plainly's actions-and-deadlines feature |
| LexiGuide AI (3JuWqehOAUn7GTVM5PrwLjiaRRg) | Legal documents: clauses, risk, plain language, Q&A. **Live link is on Vercel.** No category or lane tag. | Low. Probably non-compliant (inferred). |
| LegalLens AI (3Je8DQw0sSQc0yNzjauCZRitAGj) | Contracts: traffic-light risk ratings, document comparison. **Uses Gemini**, hosted on Amplify. Daily-life category. | Medium |
| EduLens (3JWv3O7S1hnpC1MC8TJxPYk9Ian) | College policy and scholarship rules into simple English. **No live link.** | Low |
| BillShield (3K2HVBLC9dgTs5exHAo6XGZxYzS) | Checks medical bills against the US No Surprises Act with rules only, cites the rules, generates PDF dispute letters. "No model in the decision path." | **Overlaps Plainly's medical-bill and reply-letter features.** Strong write-up. |
| Scheme Saathi (3JeD5jyLwSps2NBlPIpbmCBrTAt), Sahay AI (3JXGnWiI7JxjKGadwiEEV5Go7OB) | Government-scheme eligibility in Hindi and English, with voice output via Amazon Polly | Overlaps the "government + your language" framing |
| DataLeakCheck | Plain-language summary of data-breach exposure | Low |
| [GH] NoticeLens (https://github.com/KaveeshaEkanayake/noticelens) | Official Sinhala and English notices explained in plain language, with every claim traced to the source. Explicitly a Zero to Shipped entry. README says "**Early development… No features are implemented yet.**" | **Closest idea**, but it may not ship |
| [GH] Lapse (papi-knomic/zero-to-shipped), RemedyAI (Extraordinarytechy/remedy-ai) | Lapse: pulls expiry dates from licences and contracts, then sends reminders. RemedyAI: warranty and refund claim letters, uses Textract and Nova. | Adjacent |

Similar projects entered the other hackathon (WeMakeDevs "First Commit"), not this one: PlainRead (rental agreements) and ClearDoc (legal documents, Textract plus Bedrock).

**G. Small business, commerce, productivity (~25)**
- ShopFlow AI, OrderProof, VeriBid, ServiceForge AI, HiveGuard AI, ReachAI.
- Freelancer scope-creep detectors ×2: Alxo, and [GH] ScopeGuard.
- SmartPrice AI, TermSync, Performance Encore, Jam Notes, Surge, Signal Lens, Scout AI, Buyable, Business Entity Resolution, QueueLess, Onboard Buddy, OmniEntry, KrishiNova, property valuation engine, NxtGen Captions, SportsVueApp, Multistore, YPN (mortgage leads, reads as spam).
- [GH] Vitrina, Anchor, PANCH, Argus, Medicine Support Hub.

**H. Daily life and personal expression (~18)**
- veggie.farm, PennyWise (expense tracker), GoWise, Daily Life Enhancement Hub, PlateGap, Bookmark Library, re:Invent Planner, Wanderlust, MediaTrackerGo, LoopShelf, TontinePilot.
- Personal expression: Sibling Scene Maker, Devlog Narrator, The 1926 Diary, mochidasu.
- [GH] Full Court Press, Contextia, Rumbo a Casa.

## 4. Crowded vs. open spaces
**Crowded (VERIFIED counts):**
- AWS cost, incident and security copilots (~16 near-duplicates).
- Study tutors that turn notes into summaries, flashcards and quizzes (~8).
- Career and resume tools.
- Flood or disaster dashboards (~5).
- Generic "AI platform" or chatbot entries.

**Open:**
- **Scams, phishing, fraud: 0 of 150.**
- Immigrants and newcomers: 0. Onboard Buddy only matches because of the words "new members".
- The personal-expression category: 5 tags, the fewest.
- Daily-life: 11 tags.
- Consumer protection (money you are owed, bills you don't owe): only BillShield, plus RemedyAI on GitHub.
- Non-English-first tools for ordinary people: only a few (Scheme Saathi, AvisoAndino, TontinePilot FR, mochidasu JP, re:Invent Planner in 6 languages).

**Pattern in the most polished entries (INFERRED from reading them):** Buyable, BillShield, Misconception Map, SecondBreath, Calltree, Firsthand, mochidasu, Scheme Saathi and Rapport tend to share these traits:
- A narrow, named user and place.
- Deterministic or cited answers ("no model in the decision path", "every line quoted word for word").
- A one-click route for judges (for example, SecondBreath's `/judges` page).
- An honest limitations section.
- A live URL on an AWS domain and both required tags.

## 5. What this means for Plainly (INFERRED)
Plainly isn't going up against a crowd. Its real threats are:
1. The pattern is generic, so reviewers may have seen many document explainers.
2. OBLIGRA already covers deadlines and actions.
3. BillShield already covers medical bills and dispute letters.
4. NoticeLens covers official notices, if it ships.

The white space no one has verifiably claimed is **scam detection combined with the multilingual letter explainer and a reply draft**.

To stand apart:
- Lead with the scam check and a specific group of users, for example newcomers or non-native speakers dealing with official mail.
- Cite the exact line of the letter behind every action and deadline.
- Add a one-click sample-letter tour for judges.
- Use both tags. Social-good or daily-life fit best; daily-life has less competition.
- Keep everything on an AWS URL.

**Not found:**
- Judging weights.
- Sponsor names.
- Any Builder Center articles about specific projects beyond what the gallery API returns.