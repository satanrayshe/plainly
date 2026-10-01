# Rules frozen

- Frozen at: 2026-09-30T23:01:12+05:30 (system clock, India Standard Time). These are the final rules; they replace
  the version frozen at 2026-09-30T22:16:32+05:30 (hashes of that version are listed below for reference).
- The repository is not a git checkout, so the rules version is identified by sha256 of each file:

| File | sha256 (final, 23:01) |
|---|---|
| `backend/verifier.py` | `0b137bd0b450740eb9c3882596f75eb4fbefe17aeaf2f2835ceac4bde2fd82bb` |
| `backend/lexicon.py` | `7caf215f977efddbd554f8401384d66f1230cc7c4c8bf67528cd7445b0ff8244` |
| `backend/contacts.py` | `77b19f02ebf5853291be52fb2a89a90f94192ef8b8c4eeb0f1cd8e1847afabf6` |
| `backend/pipeline.py` | `9597c0d58507f85e85b7e3693ee72795cef1bd1bfa339932da59d0d3ca4f31cf` |
| `backend/agencies.py` | `153bfcb691f29596ab59768b1bb795771326e329b64e01750456c750c8656d69` |
| `backend/registry.json` | `c9aa3bcd333960e3b74a60e6f42f6ff2c99740eee61f9117730f74fefb87efde` |

`verifier.py`, `lexicon.py`, `contacts.py` and `pipeline.py` are the rules files named in the tuning brief;
`agencies.py` and `registry.json` are listed because they also decide verdicts. `pipeline.py`, `agencies.py` and
`registry.json` did not change in the false-positive hunt. `eval/run_eval.py` prints the first 12 characters of the
same hashes in every report.

Superseded version (22:16:32): verifier.py `934d149a…70ea64`, lexicon.py `f908bc5e…54b7d`, contacts.py
`f67c4c61…886b64`, pipeline.py `9597c0d5…31cf` (unchanged), agencies.py `153bfcb6…6d69` (unchanged), registry.json
`c9aa3bcd…efde` (unchanged).

## How the rules were tuned

- Tuned only on `eval/dev/` and `eval/synthetic/` (24 generated letters), in offline mode: fake AWS, extraction by
  the keyword reader in `eval/mock_model.py`, rules in code.
- First pass (to 22:16): 42 government-published dev examples.
- False-positive hunt (22:16 to 23:01): 25 genuine messages written from public templates and saved as
  `eval/dev/genuine_fp_*.json` (source URL in each), plus 42 further genuine probes run by hand; every probe that failed is
  kept as a regression test in `backend/tests/test_false_positives.py`. Eleven of the 25 were `likely_scam` when first run: eight under the
  22:16 rules (e-Challan SMS, HDFC card OTP SMS, I4C digital-arrest awareness SMS, SBI re-KYC SMS with the bank's own
  link, HDFC re-KYC email, I4C parcel-scam awareness SMS, Delhi Police fraud alert, SBI fraud-awareness SMS) and three
  added after the first fixes (Passport Seva police verification, I4C awareness in Hindi, US jury summons). None of
  the 25 is `likely_scam` now. What changed is listed in `docs/CONTRACT.md` ("False-positive hunt").
- IRS CP14 and CP501 wording was not used for the hunt because the holdout contains those notices.
- **`eval/holdout/` was not consulted.** No holdout file was opened, read, searched or run while the rules were
  changed, and no holdout result was produced. The holdout should be run once, with these exact hashes, and
  reported as it comes out.

## Offline results on the tuning sets

`results-offline-dev-baseline.md` is the run before any tuning. `results-offline-dev.md` is the run with the final
rules on the 67 dev files; it replaced the 22:16 report, whose headline numbers are the middle column below.

| Set | Metric | Before tuning | 22:16 rules | Final rules |
|---|---|---|---|---|
| dev scams (29) | likely_scam recall | 3/29 | 25/29 | 25/29 |
| dev | precision for likely_scam | 3/5 | 25/25 | 25/25 |
| dev | scams marked consistent_with_genuine | 2 | 0 | 0 |
| dev, original genuine (13) | marked likely_scam | 2 | 0 | 0 |
| dev, original genuine (13) | marked consistent_with_genuine | 6/13 | 7/13 | 7/13 |
| dev, genuine_fp (25) | marked likely_scam | not run | 8 of the 21 run then* | 0/25 |
| dev, genuine_fp (25) | marked consistent_with_genuine | not run | | 5/25 (20 cant_tell) |
| synthetic (12 / 12) | likely_scam recall | 10/12 | 11/12 | 11/12 |
| synthetic | genuine marked likely_scam | 0 | 0 | 0 |
| synthetic | genuine marked consistent_with_genuine | 12/12 | 12/12 | 12/12 |

\* 21 of the final 25 texts were run against the 22:16 rules before any change; the other four (TRAI DND, Passport
Seva, Hindi I4C, jury summons) were written after the first fixes.

Dev numbers show fit to examples the rules were tuned on, not accuracy on new letters. The genuine_fp texts were
written by the same person who then fixed the rules, so they are a regression check, not evidence of accuracy.

## Holdout run (the one run against these hashes)

- 2026-09-30 23:03 IST. Before the run, the sha256 of all six files above was recomputed, and every one matched.
- Command: `python eval/run_eval.py --set all --out eval/results-offline-frozen.md`, in offline mode (fake AWS,
  keyword reader). Results are written up in `eval/results.md`.
- Offline holdout: 1/12 scams read as `likely_scam`, 0 scams marked `consistent_with_genuine`, 0/11 genuine
  marked `likely_scam`, and 8/11 genuine marked `consistent_with_genuine`.
- No rule changed after the holdout was seen. The gaps it showed are listed under "Known gaps" in `eval/results.md`.
  Changing the rules now needs a new freeze and new holdout letters.
- Live (Bedrock) numbers are pending.

### Line endings: hashes from a git checkout

The hashes above are of the Windows working copy, where five of the six files have CRLF line endings.
`.gitattributes` sets `eol=lf`, so git stores the same files with LF, and the same content hashes differently
after a fresh clone. Here are the sha256 values of the committed (LF) blobs for the same frozen version:

| File | sha256 of committed LF file |
|---|---|
| `backend/verifier.py` | `056f59b0bdc4ea6b5870e7b2138b68003cb6cb9d225a05450f59b737b044343d` |
| `backend/lexicon.py` | `7caf215f977efddbd554f8401384d66f1230cc7c4c8bf67528cd7445b0ff8244` (already LF) |
| `backend/contacts.py` | `79e3df085224a6a2db619adcd32faf0097aba3cafd6bc93320d77f64b55e3fa4` |
| `backend/pipeline.py` | `b0455607bed0d13d66b3f0657c73a1381627068b337d1b9105b35fd00c62f4ab` |
| `backend/agencies.py` | `ba9c1afebcc1af2e8a03f8d3872d6dc2b3bde0dcee4463a195ac12b96d71a155` |
| `backend/registry.json` | `72f84b1aab52ede75d787f5c1fcab33428387cd3f24512c3497695c2f6e8a670` |

On a Linux or macOS checkout, `run_eval.py` prints prefixes of the LF values. On a Windows checkout with
`core.autocrlf=true`, it prints prefixes of the CRLF values.

## Option B (1 Oct 2026): what changed and what didn't

The live product now runs with `AI_MODE=off` (AWS Free plan: no Bedrock, no Textract). For that:

- **Unchanged (same sha256 as the 23:01 freeze):** `verifier.py`, `lexicon.py`, `contacts.py`, `agencies.py`,
  `registry.json`.
- **Changed:** `backend/pipeline.py`, now `752e77608a78eac098344b87986d036dde1bb6af49ed9af65d80978b1b306564`
  (LF; the working copy is LF too). It adds the `AI_MODE` switch, the text-only `/api/check` request, the rules-only
  path and template explanations, and rewords trace and flag text that said "the model". No rule, threshold or
  verdict logic changed.
- **New:** `backend/reader.py` (`5ecd9ba5285a859ee0caa726d42de59f6990e7cacb4e63092d7117456c62546b`). It is the
  keyword and date reader from `eval/mock_model.py` (the reader every offline number above was measured with), moved
  into the backend unchanged; `backend/tests/test_reader.py` checks it against `mock_model.extract` and against
  golden hashes of the old output.
- **Review fixes, 1 Oct 2026 (later):** `backend/pipeline.py` changed again, now
  `77e2dd6921b9998ee916239bb8f6ff0846efce53b925b4c3de3a2bb100ab8070` (LF). Request handling only: `/api/explain`
  accepts a larger `check` and longer `letter_text` with AI off, takes the reader's date (`today`), and a
  `sample_text` text source labels the showcase results. No rule, threshold, reader or verdict logic changed; the
  five frozen files and `reader.py` still have the hashes above, and the eval below was re-run with the same result.
- **Check:** `python eval/run_eval.py --set all --out eval/results-rules-reader.md` through the production path gives,
  for all 114 letters, the same verdict, flags, agency, deadlines, grounding and status as
  `results-offline-frozen.json`. So the frozen numbers are the production engine's numbers. `run_eval.py` now also
  prints a `reader.py` hash prefix.
- The site and `/api/check` report the engine as `rules-v<10 hex>`, a hash over the reader, rules, registry,
  templates and pipeline (`pipeline.RULES_FILES`), so it changes when any of those files change, including wording.
