from datetime import date

import pytest

import dates
import grounding

OCR = """INTERNAL REVENUE SERVICE
Notice date: September 15, 2026
You have unpaid taxes for tax year 2025. Pay the
amount due of $1,245.67 by October 6, 2026.
If you don't pay, we may charge interest."""


def test_normalize():
    assert grounding.normalize("  Pay the “amount”   DUE! ") == "pay the amount due"


@pytest.mark.parametrize("quote", [
    "Pay the amount due of $1,245.67 by October 6, 2026.",   # spans an OCR line break
    "pay the amount due of $1245.67 by october 6 2026",      # punctuation and case differ
    "Notice date: Septernber 15, 2026",                      # OCR-style typo, fuzzy match
    "If you don't pay, we may charge interest.",
])
def test_grounded(quote):
    assert grounding.is_grounded(quote, OCR)


@pytest.mark.parametrize("quote", [
    "Pay with Google Play gift cards today.",                # hallucinated
    "You will be arrested if you do not pay.",
    "",
    "paym",                                                  # too short for fuzzy matching, and not a word hit
])
def test_not_grounded(quote):
    assert not grounding.is_grounded(quote, OCR + "\npayment")


def test_best_ratio_bounds():
    assert grounding.best_ratio("amount due", OCR) == 1.0
    assert grounding.best_ratio("totally different words", OCR) < 0.85


@pytest.mark.parametrize("text, country, expected", [
    ("2026-09-30", None, date(2026, 9, 30)),
    ("September 30, 2026", "US", date(2026, 9, 30)),
    ("Sept. 30 2026", "US", date(2026, 9, 30)),
    ("30th September 2026", "IN", date(2026, 9, 30)),
    ("30-Sep-2026", "IN", date(2026, 9, 30)),
    ("30/09/2026", "IN", date(2026, 9, 30)),
    ("09/30/2026", "US", date(2026, 9, 30)),
    ("03/04/2026", "US", date(2026, 3, 4)),
    ("03/04/2026", "UK", date(2026, 4, 3)),
    ("30.09.26", "IN", date(2026, 9, 30)),
    ("no date here", None, None),
    ("31/02/2026", "IN", None),
])
def test_parse_date(text, country, expected):
    assert dates.parse_date(text, country) == expected


def test_letter_date_prefers_label():
    text = "Pay by October 6, 2026\nDate: September 15, 2026\nDear taxpayer"
    assert dates.find_letter_date(text, "US") == (date(2026, 9, 15), "September 15, 2026")


def test_letter_date_header_fallback_skips_deadlines():
    text = "INTERNAL REVENUE SERVICE\nSeptember 15, 2026\nPay by October 6, 2026"
    assert dates.find_letter_date(text, "US")[0] == date(2026, 9, 15)


def test_relative_mentions():
    found = dates.relative_mentions("Respond within thirty (30) days of the date of this notice. "
                                    "Reply within 10 business days of receipt. Pay within 24 hours.")
    assert [(f["n"], f["unit"], f["business"], f["anchor"]) for f in found] == [
        (30, "days", False, "letter_date"), (10, "days", True, "receipt"), (24, "hours", False, "letter_date")]
    hindi = dates.relative_mentions("15 दिनों के भीतर जवाब दें")
    assert hindi[0]["n"] == 15 and hindi[0]["unit"] == "days"


def test_add_days_business():
    assert dates.add_days(date(2026, 9, 25), 1, business=True) == date(2026, 9, 28)  # Fri -> Mon
    assert dates.add_days(date(2026, 9, 25), 30) == date(2026, 10, 25)


def test_deadline_dates_need_a_cue():
    text = "Notice date September 15, 2026. Pay by October 6, 2026. Tax period ending December 31, 2025."
    assert [d[0] for d in dates.deadline_dates(text, "US")] == [date(2026, 10, 6)]


def test_many_ungrounded_quotes_against_a_long_text_stay_fast():
    import random
    import time

    rng = random.Random(7)
    vocabulary = [f"{w}{i}" for i, w in enumerate(("notice", "amount", "payment", "balance", "account",
                                                   "letter", "office", "return", "refund", "penalty") * 40)]
    text = " ".join(rng.choice(vocabulary) for _ in range(3000))[:20000]
    quotes = [" ".join(rng.choice(vocabulary)[::-1] for _ in range(18)) for _ in range(20)]
    reader = grounding.Reader(text)
    started = time.perf_counter()
    assert not any(reader.is_grounded(q) for q in quotes)
    assert time.perf_counter() - started < grounding.FUZZY_BUDGET_S + 1.0


def test_reader_stops_fuzzy_matching_when_out_of_time():
    reader = grounding.Reader(OCR, fuzzy_budget_s=0)
    assert reader.is_grounded("Pay the amount due of $1,245.67 by October 6, 2026.")  # exact still works
    assert not reader.is_grounded("Notice date: Septernber 15, 2026")
    assert reader.out_of_time
