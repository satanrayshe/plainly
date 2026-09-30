# Plainly evaluation

- Generated: 2026-09-30T16:19:06+00:00
- Mode: offline: AWS faked, extraction by the keyword reader in eval/mock_model.py. These numbers measure the deterministic rules plus a crude reader, not the model; latency and tokens are not meaningful
- Rules under test (frozen, sha256 prefix): verifier.py 8ee98d2ac255, lexicon.py b6e239ae2b29, contacts.py f19ef0c88a4a, pipeline.py a8a1b4cf5b4f, registry.json c9aa3bcd3339
- Positive class for precision/recall: `likely_scam`. "Can't tell" on a scam counts as a miss for recall, never as a pass.

## Dev: government-published examples used for tuning

Real scam messages and genuine notices published by the FTC, GOV.UK, PIB Fact Check, I4C, DoT and the IRS. The rules were tuned against these, so they measure fit, not generalisation. See eval/README.md for sources.

| Metric | Value |
|---|---|
| Letters | 42 (0 errors) |
| Precision for likely_scam | 3/5 (60%) |
| Recall for likely_scam | 3/29 (10%) |
| Scam letters marked consistent_with_genuine (target 0) | **2** |
| Can't tell rate (all letters) | 29/42 (69%) |
| Genuine letters marked consistent_with_genuine | 6/13 (46%) |
| Deadline accuracy (letters with a labeled deadline) | 1/2 (50%) |
| Quote grounding (grounded / checked quotes) | 86/86 (100%) |
| Latency p50 / p95, /api/check wall clock | 5 ms / 24 ms |
| Average tokens in / out | 762 / 146 |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 3 | 2 | 24 |
| genuine | 2 | 6 | 5 |

### Misses (Dev: government-published examples used for tuning)

- `ch-hmrc-branded-verify-identity-email`: scam read as **consistent_with_genuine**. Flags: none — [source](https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house)
- `ch-identity-verification-gmail-email`: scam read as **consistent_with_genuine**. Flags: none — [source](https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house)
- `ch-kyc-kyb-verification-email`: scam read as **cant_tell**. Flags: none — [source](https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house)
- `ch-online-identification-24h-email`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (medium) — [source](https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house)
- `ch-verify-identity-now-email`: scam read as **cant_tell**. Flags: none — [source](https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house)
- `dvla-vehicle-tax-unpaid-email`: scam read as **cant_tell**. Flags: none — [source](https://www.gov.uk/government/news/dvla-releases-latest-scam-images-to-help-keep-motorists-safe-online)
- `ftc-irs-refund-offset-email`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/consumer-alerts/2024/01/irs-doesnt-send-tax-refunds-email-or-text)
- `ftc-maryland-traffic-hearing-notice`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://consumer.ftc.gov/consumer-alerts/2026/04/text-about-traffic-violation-probably-scam)
- `ftc-paypal-binance-invoice-email`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://consumer.ftc.gov/consumer-alerts/2023/05/those-urgent-emails-metamask-paypal-are-phishing-scams)
- `ftc-sunpass-toll-text`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/consumer-alerts/2024/05/text-about-overdue-toll-charges-probably-scam)
- `ftc-unpaid-toll-bill-text`: scam read as **cant_tell**. Flags: none — [source](https://consumer.ftc.gov/consumer-alerts/2025/01/got-text-about-unpaid-tolls-its-probably-scam)
- `i4c-electricity-disconnection-sms`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (info) — [source](https://www.cybercrime.gov.in/Webform/theme/resources/advisories/FakeSMSsrelatedtounpaidElectricityBilltodupecitizens.pdf)
- `i4c-job-offer-sms-cv-selected`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://www.cybercrime.gov.in/Webform/theme/resources/advisories/FraudsterssendingFakeJobOfferSMSstoperpetrateCybercrime.pdf)
- `i4c-job-offer-sms-project-manager`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://www.cybercrime.gov.in/Webform/theme/resources/advisories/FraudsterssendingFakeJobOfferSMSstoperpetrateCybercrime.pdf)
- `irs-cp01a-sample`: genuine letter read as **likely_scam**. Flags: credential_request (strong) — [source](https://www.irs.gov/pub/notices/cp01a_english.pdf)
- `irs-cp05-sample`: genuine letter read as **likely_scam**. Flags: threat_arrest (strong), unknown_contact (medium) — [source](https://www.irs.gov/pub/notices/cp05_english.pdf)
- `irs-cp21a-sample`: deadline: expected 2017-02-20, got none. Flags: urgency_short (medium) — [source](https://www.irs.gov/pub/notices/cp21a_english.pdf)
- `pib-bsnl-trai-sim-kyc-notice`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (medium) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-govt-yojana-credit-sms`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-income-tax-refund-email`: scam read as **cant_tell**. Flags: unknown_contact (medium) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-income-tax-refund-sms`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-ippb-account-blocked-pan-sms`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (medium) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-kbc-lottery-letter`: scam read as **cant_tell**. Flags: none — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-ministry-of-power-disconnection-notice`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (info) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-ncs-data-entry-job-email`: scam read as **cant_tell**. Flags: unknown_contact (medium) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-pm-yojana-aadhaar-loan-sms-hindi`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-sbi-account-blocked-sms`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-sbi-account-expire-pan-sms`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)
- `pib-sbi-yono-pan-kyc-sms`: scam read as **cant_tell**. Flags: unknown_contact (info) — [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/feb/doc202422305401.pdf)

Genuine letters left at cant_tell (safe direction, but not confirmed): 5

- `dot-cell-broadcast-test-alert`: flags unknown_contact (info)
- `irs-cp21a-sample`: flags urgency_short (medium)
- `irs-cp22a-sample`: flags urgency_short (medium)
- `irs-cp565-sample`: flags unknown_contact (medium)
- `irs-cp75-sample`: flags unknown_contact (medium)

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
| Latency p50 / p95, /api/check wall clock | 3 ms / 5 ms |
| Average tokens in / out | 558 / 168 |

| True label | likely_scam | consistent_with_genuine | cant_tell |
|---|---|---|---|
| scam | 10 | 0 | 2 |
| genuine | 0 | 12 | 0 |

### Misses (Synthetic: generated letters)

- `syn-scam-trai-sim`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (medium)
- `syn-scam-toll-text`: scam read as **cant_tell**. Flags: urgency_short (medium), unknown_contact (info)
