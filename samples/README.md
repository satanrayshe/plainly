# Sample letters

Six synthetic letters used on the landing page and the `/try/` tiles. Every one is watermarked
"SAMPLE — NOT A REAL NOTICE", has no seals or logos, and uses fictional people, addresses, account numbers,
phone numbers and handles.

| id | what it is | expected verdict |
|---|---|---|
| electricity-final-notice | India discom-style "final notice": power cut tonight, officer's personal mobile, UPI to a personal handle | likely scam |
| irs-balance-due | IRS CP14-format balance-due notice: notice date 14 Sep 2026, due 5 Oct 2026 (21 days), official phone 800-829-1040, irs.gov links | consistent with genuine |
| digital-arrest-parcel | "CBI / Customs" parcel notice: digital arrest, Skype video call, secrecy, transfer savings or USDT | likely scam |
| ai-instruction | fake refund approval with a lookalike link, a password request and a faint line aimed at AI tools | likely scam |
| sim-block-sms | phone screenshot of a "TRAI" SMS: number blocked in 2 hours, press 9, share the OTP | likely scam |
| income-tax-intimation | Income Tax Department section 143(1)(a) communication: respond within 30 days of 25 Sep 2026 on incometax.gov.in, helpdesk 1800 103 0025 | consistent with genuine |

Official details in the genuine-format letters were checked against the agencies' own pages on 2026-09-30:
IRS 800-829-1040 ([irs.gov/help/telephone-assistance](https://www.irs.gov/help/telephone-assistance)), CP14 layout
and wording ([IRS sample CP14](https://www.irs.gov/pub/notices/cp14_english.pdf)), Income Tax e-Filing and CPC
helpdesk 1800 103 0025 and +91-80-46122000
([incometax.gov.in contact us](https://www.incometax.gov.in/iec/foportal/contact-us)), and the 30-day response
window for 143(1)(a)
([e-Filing help](https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/prima%20facie%20adjustment-UM)).

## Files

- `letters/<id>.html`: self-contained source (inline CSS). The canvas size is in `<meta name="plainly:render">`:
  794x1123 CSS px (A4) for letters, 412x892 for the SMS screenshot.
- `letters/<id>.png`: rendered at device scale 2, then capped at a 2000 px long edge and under 1.5 MB.
- `letters/<id>.txt`: the letter's visible text taken from its HTML (watermark left out). It is not an OCR run.
  `run_samples.py` sends it with `text_source: "sample_text"`, so the results say "the sample letter's text" and never
  claim a reading on the device. `run_samples.py --refresh-text` rebuilds it.
- `results/<id>.json`: what the site pre-renders. The default run is the production path (`AI_MODE=off`: rules
  reader, rules, template explanations in English, Hindi and Spanish; no AWS) and writes `"mock": false`.
  `--ai-mock` (AI_MODE=on with faked Textract and Bedrock) writes to `results/mock/` so it never replaces these.

```
python scripts/render_letters.py              # all letters (Edge or Chrome, headless; needs Pillow)
python scripts/render_letters.py sim-block-sms
python scripts/run_samples.py                 # production path, no AWS -> results/<id>.json
python scripts/run_samples.py --live          # AI_MODE=on with real Textract + Bedrock (Paid plan only)
```

Read through the real on-device OCR (Tesseract.js 5.1.1, English, headless Edge, 1 Oct 2026), the PNGs of
`irs-balance-due`, `electricity-final-notice` and `digital-arrest-parcel` give the same verdicts as their `.txt`
files, in 3 to 5 s each on a desktop. The OCR text is not identical:
- `electricity-final-notice`: the red title and the bill table are not read, and the officer's mobile number breaks
  across two lines, so `callback_unofficial` is medium instead of strong. Still "Likely scam" (UPI payment to a
  personal handle, strong, plus the deadline tonight).
- `irs-balance-due`: the two-column layout merges, so the deadline quote reads "Amount due by October 5, 2026
  $1,284.60 govipay P pa pay P". The date (5 Oct 2026) and verdict are unchanged; the stray words appear in the
  calendar entry unless the person fixes the text in the box before checking.
- `digital-arrest-parcel`: same flags as the text.
- `ai-instruction` (checked during the Option B review): on-device Tesseract does not read the faint line, so the PNG
  gets no `ai_instruction` or `injection_detected_model` flag (it is still "Likely scam" from `credential_request`,
  `lookalike_domain`, `urgency_short` and `link_bait`). The published result for this sample comes from the `.txt`;
  the judges page and How it works say the rule catches instructions that reach it as text.

`ai-instruction` is published only as the PNG. Its HTML source and `.txt` contain the hidden line as text, so don't link or
copy the `.html` into the site, and never quote that line in results, pages or the write-up. `run_samples.py`
refuses to save a result that repeats it.
