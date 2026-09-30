# Evaluation

`run_eval.py` sends every labeled letter through `POST /api/check` (the same Lambda handler the site uses, called
in-process) and writes a report. Holdout and synthetic letters are always reported separately, and every miss is
listed with the flags that fired.

```
python eval/synthetic/generate.py     # only if you change the generator; letters.json is committed
python eval/run_eval.py               # offline: AWS faked      -> eval/results-offline.md (+ .json)
python eval/run_eval.py --live        # real Bedrock, us-east-1 -> eval/results.md (+ .json)
python eval/run_eval.py --set holdout
```

`--live` uses whatever AWS credentials the shell has. Letters are sent as text, so Textract is not called and
quotes are grounded against the pasted text.

## The rules are frozen

The eval only counts. It never changes a rule, threshold or registry entry, and each report records a sha256
prefix of `backend/verifier.py` and `backend/registry.json`, so a number can be traced to one rules version. If
the rules change after a run, re-run and publish the new report next to the old one; don't edit the old one.

## Offline mode

Offline, `harness.py` swaps boto3 clients for fakes before importing the backend. Bedrock is answered by
`mock_model.py`, a keyword reader that fills the `record_letter` fields with sentences copied from the letter.
Offline numbers therefore measure the deterministic rules plus a crude reader. They are useful for catching
regressions in the rules and wiring, not as a claim about accuracy. Latency and tokens are meaningless offline.
Until `backend/registry.json` exists, offline runs use `backend/tests/fixtures/registry_test.json`.
Set `PLAINLY_BACKEND_DIR` to test a different checkout of the backend.

## Metrics

- Precision and recall for `likely_scam`. A scam read as "Can't tell" is a recall miss.
- Scam letters marked `consistent_with_genuine`. This is the costly error, and the target is 0.
- "Can't tell" rate, and how many genuine letters reach `consistent_with_genuine`.
- Deadline accuracy on letters with a labeled deadline: an extracted deadline must equal the label exactly.
- Grounding: grounded quotes out of all checked quotes, from each response's `grounding` field.
- p50/p95 wall-clock latency of `/api/check` and average input/output tokens from `meta`.

## holdout/ (23 files)

Each file is `{id, label, kind, source_name, source_url, published, text_is, text, ...}`. Only examples the page
itself shows are used; `text_is` says whether the text is verbatim or a set of quoted passages joined together,
and `note` explains any connecting words we added.

Scam (12), all quoted by US government pages:

| id | source |
|---|---|
| irs-covid-treas-fund-text | [IRS COVID Tax Tip 2020-167](https://www.irs.gov/newsroom/irs-warns-people-about-a-covid-related-text-message-scam) |
| irs-unclaimed-refund-letter | [IRS IR-2023-123](https://content.govdelivery.com/accounts/USIRS/bulletins/3634dd2) |
| irs-eip-refund-email, irs-claim-refund-online-email, irs-fix-it-text | [IRS IR-2023-131](https://www.irs.gov/newsroom/taxpayers-see-wave-of-summer-email-text-scams-irs-urges-extra-caution-with-flood-of-schemes-involving-economic-impact-payments-employee-retention-credits-tax-refunds) |
| ic3-toll-smishing | [FBI IC3 PSA I-041224-PSA](https://www.ic3.gov/PSA/2024/PSA240412) |
| ftc-robocall-* (6 transcripts) | [FTC Robocall Scam Examples](https://consumer.ftc.gov/features/robocall-scam-examples) |

Genuine (11): the first two pages of IRS sample notices CP11, CP12, CP13, CP14, CP49, CP59, CP71C, CP501, CP503,
CP504 and CP523, text layer extracted verbatim from `https://www.irs.gov/pub/notices/<notice>_english.pdf`. Five
carry an `expected_deadline` taken from the "Amount due by" date printed on the notice. IRS samples use
placeholder names and IDs, and some print `1-800-xxx-xxxx` instead of a phone number, so they are harder to
confirm than a real notice.

US federal government works are in the public domain. Every file keeps its source URL.

### Coverage gaps (known)

- No India or UK items. The PIB, TRAI, MHA/I4C and HMRC pages we could fetch describe these scams (SIM
  disconnection, "digital arrest", electricity disconnection, refund phishing) but show the messages only as
  images or paraphrase them, so there was no verbatim text to use. The synthetic set covers these patterns, and
  real messages from testers (with consent, redacted) are the next thing to add.
- Six of the twelve scams are robocall transcripts, not letters or texts.
- Genuine letters are all IRS. SSA and Income Tax Department letters appear only in the synthetic set.

## synthetic/

`generate.py` writes `letters.json`: 24 letters, 12 in genuine formats (IRS, SSA, Income Tax Department) using only
the contact details those agencies publish, and 12 scam variants that mix the rules (gift cards, crypto and wire,
personal UPI handles, OTP and password requests, arrest and "digital arrest" threats, video calls, secrecy,
lookalike domains, free-mail contacts, short deadlines, hidden AI instructions). Some scams are deliberately hard:
one uses the real IRS phone number and website but demands Bitcoin, and the toll text has only a deadline and an
unknown link. The generator is seeded, so the committed file is reproducible. The same team wrote the rules and
these letters, so read the synthetic numbers as a regression check.
