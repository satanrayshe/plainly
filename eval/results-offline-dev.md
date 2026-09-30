# Plainly evaluation

- Generated: 2026-09-30T17:31:00+00:00
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
| Latency p50 / p95, /api/check wall clock | 4 ms / 24 ms |
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
| Latency p50 / p95, /api/check wall clock | 3 ms / 5 ms |
| Average tokens in / out | 695 / 210 |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 11 | 0 | 1 |
| genuine | 0 | 12 | 0 |

### Misses (Synthetic: generated letters)

- `syn-scam-toll-text`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (info)
