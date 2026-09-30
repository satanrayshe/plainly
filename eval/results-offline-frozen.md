# Plainly evaluation

- Generated: 2026-09-30T17:33:03+00:00
- Mode: offline: AWS faked, extraction by the keyword reader in eval/mock_model.py. These numbers measure the deterministic rules plus a crude reader, not the model; latency and tokens are not meaningful
- Rules under test (frozen, sha256 prefix): verifier.py 0b137bd0b450, lexicon.py 7caf215f977e, contacts.py 77b19f02ebf5, agencies.py 153bfcb691f2, pipeline.py 9597c0d58507, registry.json c9aa3bcd3339
- Positive class for precision/recall: `likely_scam`. "Can't tell" on a scam counts as a miss for recall, never as a pass.

## Dev: government-published examples used for tuning

Real scam messages and genuine notices published by the FTC, GOV.UK, PIB Fact Check, I4C, DoT and the IRS. The rules were tuned against these, so they measure fit, not generalisation. See eval/README.md for sources.

| Metric | Value |
|---|---|
| Letters | 67 (0 errors) |
| Precision for likely_scam | 25/25 (100%) |
| Recall for likely_scam | 25/29 (86%) |
| Scam letters marked consistent_with_genuine (target 0) | **0** |
| Can't tell rate (all letters) | 30/67 (45%) |
| Genuine letters marked consistent_with_genuine | 12/38 (32%) |
| Deadline accuracy (letters with a labeled deadline) | 1/2 (50%) |
| Quote grounding (grounded / checked quotes) | 120/120 (100%) |
| Latency p50 / p95, /api/check wall clock | 4 ms / 25 ms |
| Average tokens in / out | 816 / 201 |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 25 | 0 | 4 |
| genuine | 0 | 12 | 26 |

### Misses (Dev: government-published examples used for tuning)

- `ch-kyc-kyb-verification-email`: scam read as **cant_tell**. Flags: link_bait (medium) — [source](https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house)
- `ch-verify-identity-now-email`: scam read as **cant_tell**. Flags: none — [source](https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house)
- `ftc-maryland-traffic-hearing-notice`: scam read as **cant_tell**. Flags: link_bait (medium), unknown_contact (info) — [source](https://consumer.ftc.gov/consumer-alerts/2026/04/text-about-traffic-violation-probably-scam)
- `ftc-sunpass-toll-text`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/consumer-alerts/2024/05/text-about-overdue-toll-charges-probably-scam)
- `irs-cp21a-sample`: deadline: expected 2017-02-20, got none. Flags: urgency_short (medium) — [source](https://www.irs.gov/pub/notices/cp21a_english.pdf)

Genuine letters left at cant_tell (safe direction, but not confirmed): 26

- `dot-cell-broadcast-test-alert`: flags unknown_contact (info)
- `genuine_fp_delhi_police_fraud_alert`: flags urgency_short (medium)
- `genuine_fp_dvla_v11_reminder_email`: flags unknown_contact (medium)
- `genuine_fp_epfo_contribution_sms`: flags none
- `genuine_fp_hdfc_card_otp`: flags unknown_contact (info)
- `genuine_fp_hdfc_rekyc_email`: flags link_bait (medium), kyc_update_threat (medium)
- `genuine_fp_hmrc_debt_sms`: flags impersonation_mismatch (medium)
- `genuine_fp_hmrc_p800_refund_sms`: flags prize_or_refund_bait (medium)
- `genuine_fp_i4c_digital_arrest_awareness`: flags none
- `genuine_fp_i4c_hindi_digital_arrest_awareness`: flags none
- `genuine_fp_i4c_parcel_scam_awareness`: flags none
- `genuine_fp_indiapost_customs_parcel`: flags unexpected_fee_to_release (medium)
- `genuine_fp_irs_5071c_identity`: flags unknown_contact (medium)
- `genuine_fp_irs_cp2000`: flags unknown_contact (medium)
- `genuine_fp_msedcl_bill_disconnection`: flags unknown_contact (info)
- `genuine_fp_passport_police_verification`: flags none
- `genuine_fp_sbi_fraud_awareness_sms`: flags none
- `genuine_fp_sbi_rekyc_branch`: flags kyc_update_threat (medium), unknown_contact (info)
- `genuine_fp_sbi_upi_debit_alert`: flags unknown_contact (info)
- `genuine_fp_trai_dnd_registered`: flags none
- `genuine_fp_us_jury_summons`: flags threat_arrest (medium), unknown_contact (info)
- `irs-cp05-sample`: flags unknown_contact (medium)
- `irs-cp21a-sample`: flags urgency_short (medium)
- `irs-cp22a-sample`: flags urgency_short (medium)
- `irs-cp565-sample`: flags unknown_contact (medium)
- `irs-cp75-sample`: flags unknown_contact (medium)

## Holdout: government-published examples

Real scam messages quoted by the IRS, FTC and FBI IC3, and IRS sample notices as genuine letters. Nothing here was written by us, and none of it was used to write the rules. See eval/README.md for sources and coverage gaps.

| Metric | Value |
|---|---|
| Letters | 23 (0 errors) |
| Precision for likely_scam | 1/1 (100%) |
| Recall for likely_scam | 1/12 (8%) |
| Scam letters marked consistent_with_genuine (target 0) | **0** |
| Can't tell rate (all letters) | 14/23 (61%) |
| Genuine letters marked consistent_with_genuine | 8/11 (73%) |
| Deadline accuracy (letters with a labeled deadline) | 5/5 (100%) |
| Quote grounding (grounded / checked quotes) | 88/88 (100%) |
| Latency p50 / p95, /api/check wall clock | 5 ms / 22 ms |
| Average tokens in / out | 990 / 229 |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 1 | 0 | 11 |
| genuine | 0 | 8 | 3 |

### Misses (Holdout: government-published examples)

- `ftc-robocall-interest-rate`: scam read as **cant_tell**. Flags: press_to_connect (medium) — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-irs-settlement`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-ssa-suspension`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-student-loan`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-tech-support`: scam read as **cant_tell**. Flags: press_to_connect (medium) — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ftc-robocall-utility-rebate`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/features/robocall-scam-examples)
- `ic3-toll-smishing`: scam read as **cant_tell**. Flags: link_bait (medium), unknown_contact (info) — [source](https://www.ic3.gov/PSA/2024/PSA240412)
- `irs-claim-refund-online-email`: scam read as **cant_tell**. Flags: link_bait (medium) — [source](https://www.irs.gov/newsroom/taxpayers-see-wave-of-summer-email-text-scams-irs-urges-extra-caution-with-flood-of-schemes-involving-economic-impact-payments-employee-retention-credits-tax-refunds)
- `irs-covid-treas-fund-text`: scam read as **cant_tell**. Flags: none — [source](https://www.irs.gov/newsroom/irs-warns-people-about-a-covid-related-text-message-scam)
- `irs-eip-refund-email`: scam read as **cant_tell**. Flags: prize_or_refund_bait (medium) — [source](https://www.irs.gov/newsroom/taxpayers-see-wave-of-summer-email-text-scams-irs-urges-extra-caution-with-flood-of-schemes-involving-economic-impact-payments-employee-retention-credits-tax-refunds)
- `irs-unclaimed-refund-letter`: scam read as **cant_tell**. Flags: none — [source](https://content.govdelivery.com/accounts/USIRS/bulletins/3634dd2)

Genuine letters left at cant_tell (safe direction, but not confirmed): 3

- `irs-cp49-sample`: flags unknown_contact (medium)
- `irs-cp523-sample`: flags urgency_short (medium)
- `irs-cp59-sample`: flags prize_or_refund_bait (medium)

## Synthetic: generated letters

24 letters from eval/synthetic/generate.py (12 genuine-format, 12 scam variants). Written by the same team as the rules, so treat these as a regression check, not as evidence of accuracy.

| Metric | Value |
|---|---|
| Letters | 24 (0 errors) |
| Precision for likely_scam | 11/11 (100%) |
| Recall for likely_scam | 11/12 (92%) |
| Scam letters marked consistent_with_genuine (target 0) | **0** |
| Can't tell rate (all letters) | 1/24 (4%) |
| Genuine letters marked consistent_with_genuine | 12/12 (100%) |
| Deadline accuracy (letters with a labeled deadline) | 9/9 (100%) |
| Quote grounding (grounded / checked quotes) | 53/53 (100%) |
| Latency p50 / p95, /api/check wall clock | 4 ms / 5 ms |
| Average tokens in / out | 695 / 210 |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 11 | 0 | 1 |
| genuine | 0 | 12 | 0 |

### Misses (Synthetic: generated letters)

- `syn-scam-toll-text`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (info)
