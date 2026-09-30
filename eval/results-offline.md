# Plainly evaluation

- Generated: 2026-09-30T15:29:47+00:00
- Mode: offline: AWS faked, extraction by the keyword reader in eval/mock_model.py. These numbers measure the deterministic rules plus a crude reader, not the model; latency and tokens are not meaningful
- Rules under test (frozen, sha256 prefix): verifier.py 8ee98d2ac255, registry.json c9aa3bcd3339
- Positive class for precision/recall: `likely_scam`. "Can't tell" on a scam counts as a miss for recall, never as a pass.

## Holdout: government-published examples

Real scam messages quoted by the IRS, FTC and FBI IC3, and IRS sample notices as genuine letters. Nothing here was written by us, and none of it was used to write the rules. See eval/README.md for sources and coverage gaps.

| Metric | Value |
|---|---|
| Letters | 23 (0 errors) |
| Precision for likely_scam | n/a |
| Recall for likely_scam | 0/12 (0%) |
| Scam letters marked consistent_with_genuine (target 0) | **0** |
| Can't tell rate (all letters) | 14/23 (61%) |
| Genuine letters marked consistent_with_genuine | 9/11 (82%) |
| Deadline accuracy (letters with a labeled deadline) | 5/5 (100%) |
| Quote grounding (grounded / checked quotes) | 86/86 (100%) |
| Latency p50 / p95, /api/check wall clock | 9 ms / 19 ms |
| Average tokens in / out | 854 / 194 |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 0 | 0 | 12 |
| genuine | 0 | 9 | 2 |

### Misses (Holdout: government-published examples)

- `ftc-robocall-interest-rate`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-irs-settlement`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-ssa-suspension`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-student-loan`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-tech-support`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-utility-rebate`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ic3-toll-smishing`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://www.ic3.gov/PSA/2024/PSA240412)
- `irs-claim-refund-online-email`: scam read as **cant_tell**. Flags: none — [source](https://www.irs.gov/newsroom/taxpayers-see-wave-of-summer-email-text-scams-irs-urges-extra-caution-with-flood-of-schemes-involving-economic-impact-payments-employee-retention-credits-tax-refunds)
- `irs-covid-treas-fund-text`: scam read as **cant_tell**. Flags: none — [source](https://www.irs.gov/newsroom/irs-warns-people-about-a-covid-related-text-message-scam)
- `irs-eip-refund-email`: scam read as **cant_tell**. Flags: none — [source](https://www.irs.gov/newsroom/taxpayers-see-wave-of-summer-email-text-scams-irs-urges-extra-caution-with-flood-of-schemes-involving-economic-impact-payments-employee-retention-credits-tax-refunds)
- `irs-fix-it-text`: scam read as **cant_tell**. Flags: none — [source](https://www.irs.gov/newsroom/taxpayers-see-wave-of-summer-email-text-scams-irs-urges-extra-caution-with-flood-of-schemes-involving-economic-impact-payments-employee-retention-credits-tax-refunds)
- `irs-unclaimed-refund-letter`: scam read as **cant_tell**. Flags: none — [source](https://content.govdelivery.com/accounts/USIRS/bulletins/3634dd2)

Genuine letters left at cant_tell (safe direction, but not confirmed): 2

- `irs-cp49-sample`: flags unknown_contact (medium)
- `irs-cp523-sample`: flags urgency_short (medium)

## Synthetic: generated letters

24 letters from eval/synthetic/generate.py (12 genuine-format, 12 scam variants). Written by the same team as the rules, so treat these as a regression check, not as evidence of accuracy.

| Metric | Value |
|---|---|
| Letters | 24 (0 errors) |
| Precision for likely_scam | 10/10 (100%) |
| Recall for likely_scam | 10/12 (83%) |
| Scam letters marked consistent_with_genuine (target 0) | **0** |
| Can't tell rate (all letters) | 2/24 (8%) |
| Genuine letters marked consistent_with_genuine | 12/12 (100%) |
| Deadline accuracy (letters with a labeled deadline) | 9/9 (100%) |
| Quote grounding (grounded / checked quotes) | 53/53 (100%) |
| Latency p50 / p95, /api/check wall clock | 3 ms / 4 ms |
| Average tokens in / out | 558 / 168 |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 10 | 0 | 2 |
| genuine | 0 | 12 | 0 |

### Misses (Synthetic: generated letters)

- `syn-scam-trai-sim`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (medium)
- `syn-scam-toll-text`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (info)
