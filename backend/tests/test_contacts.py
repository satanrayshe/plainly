import pytest

import contacts


@pytest.mark.parametrize("a, b", [
    ("800-829-1040", "+1 (800) 829-1040"),
    ("800-829-1040", "1-800-829-1040"),
    ("800-829-1040", "800.829.1040"),
    ("800 829 1040", "+18008291040"),
    ("+91 98765 43210", "098765 43210"),
    ("+91-98765-43210", "9876543210"),
    ("91 98765 43210", "98765-43210"),
    ("0300 200 3300", "+44 300 200 3300"),
    ("0300 200 3300", "0044 300 200 3300"),
    ("1800 103 0025", "1800-103-0025"),
])
def test_same_phone(a, b):
    assert contacts.same_phone(a, b)


@pytest.mark.parametrize("a, b", [
    ("800-829-1040", "888-829-1040"),
    ("+91 98765 43210", "+91 98765 43211"),
    ("0300 200 3300", "0300 123 2040"),
])
def test_different_phone(a, b):
    assert not contacts.same_phone(a, b)


def test_phone_key_examples():
    assert contacts.phone_key("+1 (800) 829-1040") == "8008291040"
    assert contacts.phone_key("+91 98765 43210") == "9876543210"
    assert contacts.phone_key("0300 123 2040") == "3001232040"


def test_find_phones_skips_dates_ids_and_amounts():
    text = ("Call 1-800-829-1040 or +91 98765 43210.\n"
            "Notice date 2026-09-30, due 30/10/2026.\n"
            "Aadhaar 1234 5678 9012. Account number: 123456789012.\n"
            "Amount due: Rs 1,23,456.00\n"
            "Consumer No. 1500123456\n"
            "Helpline: (877) 777-4778")
    found = [p for p, _, _ in contacts.find_phones(text)]
    assert found == ["1-800-829-1040", "+91 98765 43210", "(877) 777-4778"]


def test_find_phones_stops_before_opening_hours():
    text = "Call 1800 103 0025 or +91-80-46122000 (08:00 to 20:00 hrs, Monday to Friday)."
    found = contacts.find_phones(text)
    assert [p for p, _, _ in found] == ["1800 103 0025", "+91-80-46122000"]
    assert all(text[start:end] == p for p, start, end in found)


def test_short_helpline_needs_phone_words():
    assert contacts.find_short_number("Call the helpline 19123 any time.", "19123")
    assert not contacts.find_short_number("Invoice 19123 attached.", "19123")


def test_find_urls_and_emails():
    text = ("Visit https://www.irs.gov/payments or irs-gov-refund.com/claim today.\n"
            "Write to help@irs-support.help or tax.help@gmail.com. Pay now.In case of doubt, call.")
    urls = [u for u, _, _ in contacts.find_urls(text)]
    emails = [e for e, _, _ in contacts.find_emails(text)]
    assert urls == ["https://www.irs.gov/payments", "irs-gov-refund.com/claim"]
    assert emails == ["help@irs-support.help", "tax.help@gmail.com"]


def test_upi_ids_are_not_emails():
    text = "Pay to rajesh.k@okaxis or 9876543210@ybl. Mail billing@bsesdelhi.com"
    assert [u for u, _, _ in contacts.find_upi_ids(text)] == ["rajesh.k@okaxis", "9876543210@ybl"]
    assert [e for e, _, _ in contacts.find_emails(text)] == ["billing@bsesdelhi.com"]


@pytest.mark.parametrize("host, label, suffix", [
    ("pay.irs-gov.com", "irs-gov", "com"),
    ("www.incometax.gov.in", "incometax", "gov.in"),
    ("gov.uk", "", "gov.uk"),
    ("https://www.gov.uk/pay", "", "gov.uk"),
    ("hmrc-refunds.co.uk", "hmrc-refunds", "co.uk"),
])
def test_split_host(host, label, suffix):
    assert contacts.split_host(host) == (label, suffix)


def test_domain_helpers():
    assert contacts.on_domain("sa.www4.irs.gov", "irs.gov")
    assert not contacts.on_domain("irs.gov.evil.com", "irs.gov")
    assert contacts.is_government("www.usa.gov")
    assert contacts.is_government("cybercrime.gov.in")
    assert not contacts.is_government("gov-refund.com")
    assert contacts.is_freemail("yahoo.co.in")
    assert not contacts.is_freemail("irs.gov")


BRANDS = ["irs.gov", "ssa.gov", "incometax.gov.in", "bsesdelhi.com", "gov.uk"]
WORDS = {"irs": "irs.gov", "hmrc": "gov.uk", "bses": "bsesdelhi.com"}


@pytest.mark.parametrize("host", [
    "irs.com", "irs-gov.com", "irsgov-refund.com", "lrs.gov.pay-now.net", "incometaxx.in", "incornetax.in",
    "bsesdelhi-bill.com", "bsesdeihi.com", "hmrc-tax-refund.co.uk", "xn--rs-goc.com", "іrs.com",
])
def test_lookalike_detected(host):
    assert contacts.lookalike_reason(host, BRANDS, WORDS), host


@pytest.mark.parametrize("host", [
    "irs.gov", "www.irs.gov", "sa.www4.irs.gov", "usa.gov", "www.gov.uk", "bsesdelhi.com", "gmail.com",
    "amazon.com", "firstbank.com", "reportfraud.ftc.gov", "cybercrime.gov.in", "incometax.gov.in",
])
def test_lookalike_not_detected(host):
    assert contacts.lookalike_reason(host, BRANDS, WORDS) is None, host


def test_levenshtein_and_skeleton():
    assert contacts.levenshtein("incometax", "incometaxx") == 1
    assert contacts.levenshtein("kitten", "sitting") == 3
    assert contacts.skeleton("1rs") == contacts.skeleton("irs")
    assert contacts.skeleton("paypaI") == contacts.skeleton("paypal")
    assert contacts.decode_punycode("xn--rs-goc.com") == "іrs.com"


@pytest.mark.parametrize("candidate, brand, expected", [
    ("usps", "usps", False),
    ("ups", "usps", False),       # a different courier, not a typo
    ("train", "trai", False),
    ("uspz", "usps", True),
    ("hrmc", "hmrc", True),       # swapped letters
    ("incometaxx", "incometax", True),
    ("incmetax", "incometax", True),
    ("medicaid", "medicare", True),
])
def test_near_miss(candidate, brand, expected):
    assert contacts.near_miss(candidate, brand) is expected


def test_other_couriers_are_not_lookalikes():
    words = {"usps": "usps.com", "trai": "trai.gov.in"}
    for host in ("ups.com", "www.ups.com", "train-tickets.com", "trail.org"):
        assert contacts.lookalike_reason(host, ["usps.com", "trai.gov.in"], words) is None, host
    assert contacts.lookalike_reason("usps-redelivery.com", ["usps.com"], words)


def test_addresses_scan_lines_and_placeholders_are_not_phones():
    text = ("INTERNAL REVENUE SERVICE\nHoltsville, NY 11742-9019\nCINCINNATI, OH 4599-0149\n"
            "0000 0000000 0000000000 0000000 0000\n0000000 0000\nPhone 1-800-829-0922")
    assert [p for p, _, _ in contacts.find_phones(text)] == ["1-800-829-0922"]


def test_nanp_plausibility_only_for_us():
    assert not contacts.plausible_for_country("01899954671", "US")
    assert contacts.plausible_for_country("1-800-829-1040", "US")
    assert contacts.plausible_for_country("011-3999-9707", "IN")
