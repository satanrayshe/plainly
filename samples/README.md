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
- `results/<id>.json`: pipeline output the site pre-renders. Live runs write here; offline runs write to
  `results/mock/` so they never replace live results.

```
python scripts/render_letters.py              # all letters (Edge or Chrome, headless; needs Pillow)
python scripts/render_letters.py sim-block-sms
python scripts/run_samples.py --live          # after AWS is connected
python scripts/run_samples.py                 # offline check of the wiring
```

`ai-instruction` is published only as the PNG. Its HTML source contains the hidden line as text, so don't link or
copy the `.html` into the site, and never quote that line in results, pages or the write-up. `run_samples.py`
refuses to save a result that repeats it.
