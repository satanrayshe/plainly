# Plainly evaluation: offline run on the frozen rules

**Live numbers are pending.** This run used mock mode: AWS was faked and a keyword stand-in did the reading that
Amazon Nova does in production. The results below check the rules and wiring. They don't measure the product.
The live run (real Bedrock) comes after AWS is connected, and those will be the numbers we publish.

## What was run

- **When:** 2026-09-30, 23:03 IST (17:33 UTC). This was the first and only run with the frozen rules.
- **Command:** `python eval/run_eval.py --set all --out eval/results-offline-frozen.md`. The report and its
  per-letter JSON (`eval/results-offline-frozen.md` and `.json`) are the raw output. This file is written from
  them.
- **Rules:** Before the run, I recomputed the sha256 of all six files listed in `eval/RULES_FROZEN.md` (frozen
  23:01:12 IST). All six matched:

  | File | sha256 |
  |---|---|
  | `backend/verifier.py` | `0b137bd0b450740eb9c3882596f75eb4fbefe17aeaf2f2835ceac4bde2fd82bb` |
  | `backend/lexicon.py` | `7caf215f977efddbd554f8401384d66f1230cc7c4c8bf67528cd7445b0ff8244` |
  | `backend/contacts.py` | `77b19f02ebf5853291be52fb2a89a90f94192ef8b8c4eeb0f1cd8e1847afabf6` |
  | `backend/pipeline.py` | `9597c0d58507f85e85b7e3693ee72795cef1bd1bfa339932da59d0d3ca4f31cf` |
  | `backend/agencies.py` | `153bfcb691f29596ab59768b1bb795771326e329b64e01750456c750c8656d69` |
  | `backend/registry.json` | `c9aa3bcd333960e3b74a60e6f42f6ff2c99740eee61f9117730f74fefb87efde` |

- **No rule changed after the holdout results came in.** Gaps the holdout exposed are listed under
  [Known gaps](#known-gaps) and not fixed. A fix would need a new freeze and new holdout letters, because these
  23 have now been seen.

### What mock mode means

- **Reader:** In production, Amazon Nova (Bedrock, forced `record_letter` tool call) reads the letter and quotes
  it. In mock mode, `eval/mock_model.py` does that job instead. It is a keyword and date-regex reader that copies
  sentences out of the letter. It doesn't understand what a letter means, so anything the rules only learn from the
  model's reading (a link hidden behind "click here", a payment demand phrased in an unusual way) is caught only when
  one of its keywords happens to match.
- **Rules:** The deterministic rules (regex in `lexicon.py`, checks in `verifier.py` and `contacts.py`, registry
  match in `agencies.py`) are the real production code.
- **Meaningless figures:** Latency, token counts, and the model name printed in each trace are not real.
  Quote grounding is 100% by construction, because the fake only quotes text it copied.
- **What live mode might change:** A real model may find signals the keyword reader misses (for example, that an
  unexpected "rebate check" is bait), and it may also quote things the fake would not. Live numbers can be better or
  worse in either direction.

### Scoring

The positive class is `likely_scam`. A scam read as "Can't tell" counts as a recall miss, never as a pass. The worst
error is a scam marked `consistent_with_genuine`, and the target for it is 0. How the verdict works: strong flags
are worth 3 points and medium flags 1. A total of 3 or more gives `likely_scam`. `consistent_with_genuine` needs a
matched agency, at least one of its official contacts in the letter, and 0 points.

## Headline

| Set | Scams → likely_scam (recall) | Precision | Scams marked consistent_with_genuine | Genuine → likely_scam | Genuine → consistent_with_genuine |
|---|---|---|---|---|---|
| **Holdout (23), never used for tuning** | **1/12 (8%)** | 1/1 | **0** | 0/11 | 8/11 |
| Dev (67), used for tuning | 25/29 (86%) | 25/25 | 0 | 0/38 | 12/38 |
| Synthetic (24), written by us | 11/12 (92%) | 11/11 | 0 | 0/12 | 12/12 |

Offline, the rules are safe and weak. No letter in any set was wrongly called a scam, and no scam was called
genuine. But on the one set the rules were never tuned on, 11 of 12 real scams came out "Can't tell". The high dev
and synthetic recall mostly shows how well the rules fit the examples they were tuned on.

## Holdout: never used for tuning

These are 12 scam messages quoted by the IRS, FTC and FBI IC3, plus 11 genuine IRS sample notices. Sources are in
`eval/README.md` and in each `eval/holdout/*.json`. No rule was written or tuned against these letters.

| Metric | Value |
|---|---|
| Letters | 23 (0 errors) |
| Precision for likely_scam | 1/1 (100%) |
| Recall for likely_scam | 1/12 (8%) |
| Scam letters marked consistent_with_genuine (target 0) | **0** |
| Can't tell rate (all letters) | 14/23 (61%) |
| Genuine letters marked consistent_with_genuine | 8/11 (73%) |
| Deadline accuracy (5 letters with a labeled deadline) | 5/5 (100%) |
| Quote grounding | 88/88 (100%, by construction offline) |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 1 | 0 | 11 |
| genuine | 0 | 8 | 3 |

**Caught (1):** `irs-fix-it-text` ("IRS: You federal return was ban-by the IRS… Click this link."). A hidden link in
a message that names the IRS scores as strong `link_bait`. That is 3 points on one flag.

### Holdout misses, with reasons

Every missed scam got `cant_tell`, which is the safe direction. The reason is in each row.

| Letter | Flags (points) | Why it was missed |
|---|---|---|
| `ftc-robocall-interest-rate` | press_to_connect (1) | "Press 1 now" is caught. The lure ("qualified… for interest rate reduction") and the pressure ("final courtesy call") match no rule. There are no contacts and no agency. |
| `ftc-robocall-irs-settlement` | none (0) | The IRS is matched by name, but the call gives no number or link. `impersonation_mismatch` only fires when a letter names an agency and gives a contact (a phone, link or sender address) that isn't the agency's. No rule covers "your tax debt can be settled for you". |
| `ftc-robocall-ssa-suspension` | none (0) | The SSA is matched by name. "We will be suspending your Social Security Number" is a known scam claim (SSA doesn't suspend numbers), but no rule has it. "If you want more information about this case, press 1." doesn't match `press_to_connect`, which needs "now" or "to speak / connect / …" after the digit. |
| `ftc-robocall-student-loan` | none (0) | "Alternative federal student loan repayment options" with "automated approval technology". It makes no demand, gives no contact and names no agency, so nothing fires. |
| `ftc-robocall-tech-support` | press_to_connect (1) | "Press 1 to connect to Apple Support Advisor" is caught. Apple is a company, not an agency in the registry, and nothing else fires. |
| `ftc-robocall-utility-rebate` | none (0) | "Press 1 to get your rebate check" isn't matched: "to get" is not one of the `press_to_connect` verbs. "Rebate check" isn't one of the `prize_or_refund_bait` lure words. No utility is named. |
| `ic3-toll-smishing` | link_bait (1), unknown_contact (info) | The unknown `.com` link counts only as medium, because no agency is matched to call it "not the agency's". The "$50 late fee" threat is not a rule. This is the same gap as the synthetic and dev toll texts. |
| `irs-claim-refund-online-email` | link_bait (1) | "Click below to claim your tax refund" is caught as medium. The name "IRS" never appears, so no agency is matched. "Within 3 days… will be cancelled" doesn't trigger `urgency_short`, which fires on hours, one or two days, or "today". `prize_or_refund_bait` did not fire either: it needs an amount or a word like "approved" or "pending" in the same sentence as the refund, and neither refund sentence has one. |
| `irs-covid-treas-fund-text` | none (0) | "Received a direct deposit of $1,200 from COVID-19 TREAS FUND… Continue here to accept this payment". The link was cut from the quote, "direct deposit" isn't a refund lure word, and "continue here" isn't a link request the keyword reader knows. |
| `irs-eip-refund-email` | prize_or_refund_bait (1) | "You will receive a tax refund of $976.00" is caught as medium. "Sender : INTERNAL REVENUE SERVICE" has no address, so the check that the sender is on an official domain has nothing to compare. The "submit the document we need" ask is not a credential request. |
| `irs-unclaimed-refund-letter` | none (0) | It asks for a photo of your driver's licence, to be given to a "Filing Agent". `credential_request` covers secrets (passwords, PINs, OTPs, CVVs), not ID documents. "This notice is in relation to your unclaimed refund" has no claim, click or submit verb in the same sentence, and `prize_or_refund_bait` needs one. No agency is named. |

### Genuine holdout letters left at "Can't tell" (not misses, but close)

Each of these sits at 1 point. One more medium flag would make it `likely_scam`.

| Letter | Flag | Why |
|---|---|---|
| `irs-cp49-sample` | unknown_contact (medium) | 1-800-829-0922 and 1-800-829-3676 are IRS numbers, but they aren't in `registry.json`. This is a registry gap. |
| `irs-cp523-sample` | urgency_short (medium) | The genuine notice prints "Payment Due Immediately". |
| `irs-cp59-sample` | prize_or_refund_bait (medium) | The keyword reader quoted "The same rule applies to a right to claim refundable…". This rule is new since the pre-tuning run, and it is the only holdout letter that got worse: the pre-tuning run called it `consistent_with_genuine`. |

### Holdout history

`eval/results-offline.md` holds the one earlier holdout run. It was produced offline at 15:29 UTC under the
pre-tuning rules (verifier `8ee98d2ac255`) and committed before tuning started, so the file was in the repo while
the rules were tuned. The tuning reports state that no one opened, read or searched holdout files or results.
That earlier run scored 0/12 recall and 9/11 genuine `consistent_with_genuine`. With the frozen rules it is 1/12
and 8/11. The only differences are the one new catch (`irs-fix-it-text`), four scams that went from 0 to 1 point,
and `irs-cp59-sample` (above).

## Dev: used for tuning

This set has 29 real scam messages (FTC, GOV.UK, PIB Fact Check, I4C) and 38 genuine messages: 13 published IRS
and DoT examples and 25 written from public templates for the false-positive hunt. The rules were tuned on these,
so the numbers show fit, not accuracy.

| Metric | Value |
|---|---|
| Letters | 67 (0 errors) |
| Precision for likely_scam | 25/25 (100%) |
| Recall for likely_scam | 25/29 (86%) |
| Scam letters marked consistent_with_genuine (target 0) | **0** |
| Can't tell rate (all letters) | 30/67 (45%) |
| Genuine letters marked consistent_with_genuine | 12/38 (32%) |
| Deadline accuracy (2 letters with a labeled deadline) | 1/2 (50%) |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 25 | 0 | 4 |
| genuine | 0 | 12 | 26 |

### Dev misses, with reasons

| Letter | Flags (points) | Why it was missed |
|---|---|---|
| `ch-verify-identity-now-email` | none (0) | It copies Companies House's genuine wording word for word. The scam is in the links, which the published screenshot doesn't show. The source notes expect `cant_tell` at best. |
| `ch-kyc-kyb-verification-email` | link_bait (1) | It has no threat, payment request or credential word, just a "Start KYC/KYB" link. Companies House is not in the registry, so the link can't be judged "not the agency's". |
| `ftc-maryland-traffic-hearing-notice` | link_bait (1), unknown_contact (info) | This fake court notice reads like a real one. "Scan the QR code" counts as medium. Maryland courts aren't in the registry, so the phone number can't be checked. |
| `ftc-sunpass-toll-text` | none (0) | The link is blurred on the FTC page and transcribed as `[…]`, so there is no link to judge. The late-fee threat is not a rule. |
| `irs-cp21a-sample` (deadline) | urgency_short (1) | Expected deadline 2017-02-20, got none. The sample prints "Amount due February 20, 2017" under a notice date of January 30, 2019, and no deadline came out of it. The verdict (`cant_tell`, from "What you need to do immediately") isn't a miss. |

The 26 genuine dev letters left at `cant_tell` are listed with their flags in `eval/results-offline-frozen.md`.
None has more than 2 points.

## Synthetic: written by us

These 24 letters come from `eval/synthetic/generate.py`: 12 in genuine formats (IRS, SSA, Income Tax Department)
and 12 scam variants. The same team wrote them and the rules, so they are a regression check only.

| Metric | Value |
|---|---|
| Letters | 24 (0 errors) |
| Precision for likely_scam | 11/11 (100%) |
| Recall for likely_scam | 11/12 (92%) |
| Scam letters marked consistent_with_genuine (target 0) | **0** |
| Can't tell rate (all letters) | 1/24 (4%) |
| Genuine letters marked consistent_with_genuine | 12/12 (100%) |
| Deadline accuracy (9 letters with a labeled deadline) | 9/9 (100%) |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 11 | 0 | 1 |
| genuine | 0 | 12 | 0 |

### Synthetic misses, with reasons

| Letter | Flags (points) | Why it was missed |
|---|---|---|
| `syn-scam-toll-text` | urgency_short (1), unknown_contact (info) | "Settle your balance within 24 hours at https://tollpay-services-center.com" names no agency. The link is only an unchecked contact: `link_bait` didn't fire on "settle … at <link>". This was built as a hard case on purpose. |

## Known gaps

These showed up in the holdout run. None was fixed, because the rules are frozen.

1. **Recorded-call scripts.** Six of the 12 holdout scams are robocall transcripts, and the rules are built for
   letters and texts. `press_to_connect` needs "now" or one of a few verbs after the digit, so "press 1." and
   "press 1 to get…" are missed. Offers such as debt settlement, loan relief, rate reduction and rebates have no rule.
2. **"Suspend your Social Security number".** The SSA says it never does this, but no rule covers the claim.
3. **Toll and late-fee texts.** Across dev, synthetic and holdout, this is the most repeated miss. An unknown
   `.com` link from an unnamed toll service, plus a late-fee threat, scores 1 point at most.
4. **Links when no agency is matched.** A visible unknown link scores medium when no agency is named, but a hidden
   "click this link" in a message naming the IRS scores strong. So a scam that doesn't name an agency is judged
   more leniently.
5. **Money-waiting lures.** "Rebate check" and "direct deposit of $1,200… accept this payment" don't match the lure
   words. A refund sentence needs an amount or a word like "approved" or "pending", plus a claim or click verb, all
   in the same sentence. So "Claim your tax refund online" and "your unclaimed refund" pass.
6. **Requests for ID documents.** A request for a driver's licence photo to a third party isn't
   `credential_request`, which covers secrets only.
7. **Sender names with no address.** "Sender : INTERNAL REVENUE SERVICE" with no address or other contact can't be
   checked, so it passes silently.
8. **Missing IRS numbers.** 1-800-829-0922 and 1-800-829-3676 are missing from `registry.json`, so genuine IRS
   notices that print them get a medium `unknown_contact`. An earlier report also noted the numbers on CP2000 and
   5071C as missing.
9. **`prize_or_refund_bait` on genuine refund wording.** A genuine CP59 lost `consistent_with_genuine` because of
   a sentence about the right to claim a refund. Several genuine letters are one medium flag away from
   `likely_scam`.
10. **Holdout coverage.** The holdout has no India or UK items, and its genuine letters are all IRS samples. The
    gaps above are US-only evidence.

## Reproduce

```
python eval/run_eval.py --set all --out eval/results-offline-frozen.md   # offline, as above
python eval/run_eval.py --live --out eval/results-live.md                 # live, after AWS is connected
```

`--live` writes to `eval/results.md` by default. Use `--out` so this file is kept, then publish the live numbers
next to it.
