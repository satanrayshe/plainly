"""False-positive hunt (2026-09-30): genuine official messages that the frozen rules read as likely_scam.

Each case here was a likely_scam before the fix named next to it. The messages are in eval/dev/genuine_fp_*.json
(written from public templates; source URL in each file). They run through verify() with the offline keyword reader
(eval/mock_model.py) as the model, because most of these false positives came through model quotes that skipped the
negation checks the code applies to its own matches. Scam counterparts check that each fix did not open a hole.
"""
import json
import sys
from pathlib import Path

import pytest

from conftest import BACKEND, TODAY, flag, rules_of

import agencies  # noqa: E402
import verifier  # noqa: E402

EVAL = BACKEND.parent / "eval"
sys.path.insert(0, str(EVAL))
import mock_model  # noqa: E402

REAL_REGISTRY = agencies.load_registry(BACKEND / "registry.json")
MOCK_REGISTRY = mock_model.load_registry(BACKEND / "registry.json")
GENUINE_FP_FILES = sorted((EVAL / "dev").glob("genuine_fp_*.json"))


def run(text, extraction="mock"):
    """verify() on pasted text with the real registry; extraction from the keyword reader unless given."""
    if extraction == "mock":
        extraction = mock_model.extract(text, MOCK_REGISTRY)
    return verifier.verify(text, extraction or {}, grounding_source="pasted_text", today=TODAY,
                           registry=REAL_REGISTRY)


def test_there_are_25_genuine_fp_cases():
    assert len(GENUINE_FP_FILES) == 25


@pytest.mark.parametrize("path", GENUINE_FP_FILES, ids=lambda p: p.stem)
def test_genuine_fp_dev_case_is_not_likely_scam(path):
    case = json.loads(path.read_text(encoding="utf-8"))
    assert case["label"] == "genuine" and case["source_url"].startswith("https://")
    result = run(case["text"])
    assert result["verdict"] != "likely_scam", [(f["rule"], f["severity"], f["quote"]) for f in result["flags"]]


# Further genuine wording found in the same hunt (not saved as dev files); each was likely_scam before its fix.
MORE_GENUINE = [
    # CBI denies the threat inside the match ("CBI does not issue arrest ..."); "If someone threatens you with ..."
    "The CBI does not issue arrest warrants over phone, video call or WhatsApp, and never asks you to pay money to "
    "close a case. If someone threatens you with digital arrest, call 1930. -CBI",
    # the keyword reader quotes "Delhi Traffic Police: e-Challan No" as a threat: the police as sender, no threat
    "Delhi Traffic Police: e-Challan No. DL12345260930101 of Rs 2000 is pending against vehicle DL01AB1234. Unpaid "
    "challans are sent to the Virtual Court and may be taken up at the National Lok Adalat. Pay at "
    "https://echallan.parivahan.gov.in.",
    # "police ... verification" is a passport service step
    "Your passport application has been sent to the police station for verification. -Passport Seva",
]


@pytest.mark.parametrize("text", MORE_GENUINE)
def test_more_genuine_wording_is_not_likely_scam(text):
    assert run(text)["verdict"] != "likely_scam"


# ---------------------------------------------------------------- model quotes get the code's negation test

def test_model_credential_quote_negated_by_request_verb_counts_nothing():
    text = "482913 is OTP for txn of INR 2,499.00 at AMAZON. Do not share OTP for security reasons. -HDFC Bank"
    result = run(text, {"credential_requests": [{"quote": "Do not share OTP for security reasons"}]})
    assert "credential_request" not in rules_of(result)


def test_model_credential_quote_that_asks_still_counts():
    text = "Dear customer, share the OTP you receive with our officer to stop the block. -Bank"
    result = run(text, {"credential_requests": [{"quote": "share the OTP you receive with our officer"}]})
    assert flag(result, "credential_request")["severity"] == "strong"


def test_model_safe_account_quote_under_never_ask_counts_nothing():
    text = ("Officers never ask you to transfer money to a 'safe account'. Report such calls at "
            "www.cybercrime.gov.in or call 1930.")
    result = run(text, {"payment_requests": [{"method": "bank transfer to 'safe' account",
                                              "quote": "Officers never ask you to transfer money to a 'safe account'"}]})
    assert "payment_crypto_wire" not in rules_of(result)


def test_model_link_quote_that_says_do_not_click_counts_nothing():
    text = "SBI never asks you to share OTP. Do not click on links in SMS asking you to update KYC. -SBI"
    result = run(text, {"link_requests": [{"quote": "Do not click on links in SMS asking you to update KYC"}]})
    assert "link_bait" not in rules_of(result)


def test_model_threat_quote_of_a_sender_name_counts_nothing():
    text = "e-Challan No. DL123 of Rs 2000 issued. Pay at https://echallan.parivahan.gov.in.\n-Delhi Traffic Police"
    result = run(text, {"threats": [{"quote": "-Delhi Traffic Police"}]})
    assert "threat_arrest" not in rules_of(result)


def test_model_threat_quote_naming_a_consequence_still_counts():
    text = "Officers will take you into custody tonight if you do not cooperate."
    result = run(text, {"threats": [{"quote": "Officers will take you into custody tonight"}]})
    assert flag(result, "threat_arrest")["severity"] == "strong"


# ---------------------------------------------------------------- awareness messages quote the scam's words

@pytest.mark.parametrize("text", [
    "Beware of digital arrest! If you get a call saying your parcel contains drugs and the CBI will arrest you, it "
    "is a scam. Do not transfer any money. Report at cybercrime.gov.in or call 1930. -I4C",
    "Alert: Fraudsters pretending to be police may say a warrant has been issued against you and ask you to stay on "
    "the video call. Disconnect and call 1930. -Delhi Police",
    "Cyber Dost alert: There is no such thing as a 'digital arrest'. Police, CBI, Customs or RBI officers never "
    "question or arrest anyone over a video call. -I4C, MHA",
    "प्रिय नागरिक, डिजिटल अरेस्ट जैसी कोई चीज़ नहीं होती। पुलिस, सीबीआई या कस्टम अधिकारी वीडियो कॉल पर गिरफ्तार नहीं करते। "
    "ऐसी कॉल आए तो 1930 पर शिकायत करें। -I4C",
])
def test_awareness_message_raises_no_strong_flag(text):
    result = run(text, {})
    assert not rules_of(result, "strong"), result["flags"]


@pytest.mark.parametrize("text", [
    "CBI officer speaking. A warrant has been issued against you. Stay on the video call and do not tell anyone.",
    "This is not a scam. The police will arrest you today unless you pay Rs 50,000.",
    "आपके खिलाफ वारंट जारी हुआ है, आपको गिरफ्तार किया जाएगा। किसी को न बताएं।",
])
def test_real_threats_still_strong(text):
    assert "threat_arrest" in rules_of(run(text, {}), "strong")


def test_video_call_negated_by_verb_list():
    text = "Police officers never question or arrest anyone over a video call."
    assert "video_call_demand" not in rules_of(run(text, {}))


def test_negated_verb_then_or_you_still_resumes():
    text = "Do not contact anyone or you will be arrested within 24 hours."
    assert "threat_arrest" in rules_of(run(text, {}), "strong")


# ---------------------------------------------------------------- cut-off, dates, bank domains, branch route

def test_denied_cutoff_is_not_a_cutoff():
    text = "Do not click on links in SMS to update KYC. Your account will not be blocked for KYC through SMS. -SBI"
    assert "kyc_update_threat" not in rules_of(run(text))


def test_deadline_quoted_as_letter_date_does_not_make_urgency():
    text = ("Dear Customer, please update KYC at your home branch or on www.onlinesbi.sbi before 31-10-2026. -SBI")
    result = run(text, {"letter_date": {"value": "2026-10-31", "quote": "before 31-10-2026"}})
    assert result["extracted"]["letter_date"] is None
    assert "urgency_short" not in rules_of(result)


@pytest.mark.parametrize("host", ["www.onlinesbi.sbi", "netbanking.hdfc.bank.in", "hdfc.bank.in"])
def test_restricted_bank_domains_are_official(host):
    text = f"Dear Customer, KYC for your account is due. Click https://{host} to update KYC. -Bank"
    result = run(text)
    assert "link_bait" not in rules_of(result)


def test_bank_in_lookalike_outside_restricted_suffix_still_counts():
    text = "Dear Customer, your account will be blocked today. Click https://hdfc-bank-in.xyz/kyc to update KYC."
    assert run(text)["verdict"] == "likely_scam"


def test_branch_route_keeps_hidden_link_kyc_reminder_below_scam():
    text = ("HDFC Bank\nDear Customer,\nYour KYC is due for update as per RBI guidelines. Update it through "
            "NetBanking or visit your nearest branch.\nClick here to update KYC\nFailing which, your account may be "
            "put on hold.")
    result = run(text)
    assert result["verdict"] != "likely_scam"
    assert flag(result, "link_bait")["severity"] == "medium"


def test_hidden_link_kyc_threat_without_branch_still_scam():
    text = ("Dear Customer,\nYour KYC is due for update as per RBI guidelines.\nClick here to update KYC\n"
            "Failing which, your account will be blocked.")
    assert run(text)["verdict"] == "likely_scam"


# ---------------------------------------------------------------- threats: passport, jury summons

def test_passport_police_verification_is_not_a_threat():
    text = ("Dear Applicant, your passport application has been forwarded to the police for verification. The "
            "police verification officer will visit your address. -Passport Seva")
    assert "threat_arrest" not in rules_of(run(text, {}))


def test_forwarded_to_police_without_verification_is_still_a_threat():
    text = "Your case has been forwarded to the police. Pay the fine now."
    assert "threat_arrest" in rules_of(run(text, {}), "strong")


JURY = ("SUPERIOR COURT OF CALIFORNIA, COUNTY OF LOS ANGELES\nJury Summons\nDate: September 20, 2026\nYou are "
        "summoned to appear for jury service on November 2, 2026. Respond online at www.lacourt.org within 10 days. "
        "Failure to respond to this summons may result in a fine, and the court may issue a bench warrant.")


def test_warrant_as_consequence_of_ignoring_a_real_deadline_is_medium():
    result = run(JURY)
    assert flag(result, "threat_arrest")["severity"] == "medium"
    assert result["verdict"] != "likely_scam"


def test_warrant_with_short_deadline_stays_strong():
    text = ("Jury Services\nFailure to respond within 24 hours will result in a bench warrant for your arrest. "
            "Call 555-201-3344 now.")
    assert flag(run(text, {}), "threat_arrest")["severity"] == "strong"
