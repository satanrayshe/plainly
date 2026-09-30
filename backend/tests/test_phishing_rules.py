"""Link, lure and call-back rules: each one with letters that should trip it and genuine wording that must not.

The genuine phrasing below is how real notices talk (IRS "pay online at www.irs.gov/payments", Income Tax "log in
to the e-Filing portal", SBI alerts that say "never share your OTP"). None of it may reach likely_scam.
"""
import pytest

from conftest import flag, rules_of, trace_step

IRS_HEADER = "Internal Revenue Service\nDepartment of the Treasury\n"
ITD_HEADER = "Income Tax Department\nCentralized Processing Centre\n"

GENUINE = [
    IRS_HEADER + "Notice date September 15, 2026\nPay the amount due by October 15, 2026. You can pay online now at "
                 "www.irs.gov/payments. If you disagree, call 800-829-1040.",
    IRS_HEADER + "You may be eligible for a refund of up to $6,431. Complete the worksheet on page 3 and mail it "
                 "to us. Visit www.irs.gov/cp09 for more information.",
    IRS_HEADER + "You can check your refund status at www.irs.gov/refunds. If you haven't received your refund "
                 "after 60 days, you can call us at the number listed above.",
    IRS_HEADER + "Keep your number private and don't give it to anyone other than a tax professional. "
                 "When you file, enter the IP PIN in the correct place. If you don't have to file a tax return, "
                 "you won't need to use your IP PIN.",
    IRS_HEADER + "Report fraudulent activity to your local police or sheriff's department.",
    ITD_HEADER + "Date of issue: 11-09-2026\nA refund of Rs. 7,861 has been determined and will be credited to your "
                 "pre-validated bank account. No action is required. You can check the refund status after logging "
                 "in to https://www.incometax.gov.in. For queries call 1800 103 0025.",
    ITD_HEADER + "Date of issue: 11-09-2026\nPlease log in to the e-filing portal and submit your response within "
                 "30 days. Visit https://www.incometax.gov.in (Pending Actions > e-Proceedings).",
    "SBI never asks for your OTP, PIN or password. Do not click on links in messages that ask you to update KYC. "
    "Report fraud at cybercrime.gov.in or call 1930. -SBI",
    "Dear Customer, KYC for your SBI account is due. Please visit your home branch with your documents to avoid "
    "restrictions on your account. -SBI",
    "Rs 5,000 debited from A/c XX1234 on 30-09-26. If you did not make this transaction, call 1800 1234 to block "
    "your card. -SBI",
    "BSES Rajdhani Power Limited\nYour bill of Rs 2,340 is due on 15/10/2026. Pay at www.bsesdelhi.com or the BSES "
    "app. For supply complaints call 19123.",
    "SancharSathi Portal - A Govt. of India initiative. Visit www.sancharsaathi.gov.in to know active mobile "
    "connections in your name - DoT GoI",
    "For help in English press 1, para español oprima 2. Call 800-829-1040.",
    "Your refund of Rs 499 has been credited to your account. Thank you for shopping with us.",
    "We are pleased to offer you the position of Analyst at Acme Ltd. Your salary will be Rs 6,00,000 a year. "
    "Please sign and return this letter.",
]


@pytest.mark.parametrize("text", GENUINE)
def test_genuine_phrasing_never_likely_scam(check, text):
    assert check(text)["verdict"] != "likely_scam"


# ---------------------------------------------------------------- link_bait

@pytest.mark.parametrize("text", [
    "Dear customer your account has been blocked today, please update your PAN. Click here https://bit.ly/3mP8DhG",
    "You are due a refund of Rs. 15,490. Please update your bank account information by visiting the link below.\n"
    "https://bit.ly/20wpYK6",
    "Your vehicle has an unpaid toll. Please reply Y, then exit the SMS and open it again to activate the link.",
    "Pay your fine now. Or copy the link to your Safari browser and open it.",
])
def test_link_bait_strong(check, text):
    f = flag(check(text), "link_bait")
    assert f["severity"] == "strong"


def test_link_bait_strong_when_registry_agency_hides_link(check):
    result = check(IRS_HEADER + "You are due a refund of $650.00. Fill your document in this link.\nCheck Your Refund")
    assert flag(result, "link_bait")["severity"] == "strong"
    assert result["verdict"] == "likely_scam"


def test_link_bait_strong_when_hidden_link_and_block_threat(check):
    result = check("Attention: Your Wallet Has been Blocked!\nYou will lose all of your funds if you do not act.\n"
                   "Recover My Wallet Now")
    assert flag(result, "link_bait")["severity"] == "strong"


@pytest.mark.parametrize("text", [
    "Acme Stores\nClick here to claim your reward: https://acme-rewards.com/claim",
    "Please update your bank account information by visiting the link below.\nhttps://refund-status-now.xyz/claim",
])
def test_link_bait_medium_for_unknown_site_without_agency(check, text):
    result = check(text)
    assert flag(result, "link_bait")["severity"] == "medium"
    assert result["verdict"] != "likely_scam"


@pytest.mark.parametrize("text", [
    IRS_HEADER + "Visit www.irs.gov/payments to pay your balance.",
    ITD_HEADER + "To update your bank account, log in to the e-Filing portal and click Profile. "
                 "Visit https://www.incometax.gov.in.",
    "Do not click on links in messages that ask you to verify your account.",
    "Visit www.sancharsaathi.gov.in to check the SIMs in your name.",
])
def test_link_bait_negative(check, text):
    result = check(text)
    assert "link_bait" not in rules_of(result)
    assert trace_step(result, "rule:link_bait")["status"] == "pass"


def test_link_bait_model_quote_is_checked_in_code(check):
    ex = {"link_requests": [{"quote": "Proceed to claim at https://bit.ly/abc"}]}
    result = check("Dear taxpayer\nProceed to claim at https://bit.ly/abc", ex)
    assert flag(result, "link_bait")["severity"] == "strong"


def test_link_bait_ungrounded_model_quote_counts_nothing(check):
    ex = {"link_requests": [{"quote": "Click this link to verify your account"}]}
    result = check("Acme Stores\nYour order has shipped.", ex)
    f = flag(result, "link_bait")
    assert f["grounded"] is False and f["severity"] == "info"


# ---------------------------------------------------------------- shortened_or_raw_link

@pytest.mark.parametrize("url", ["https://bit.ly/20wpYK6", "http://surl.li/iccpf", "https://cm91.short.gy/KYC_PAN",
                                 "https://sayv-ayec-2af.vercel.app", "http://203.0.113.9/login",
                                 "tinyurl.com/2v5bn795"])
def test_shortened_link_positive(check, url):
    f = flag(check(f"Your parcel is waiting. Details: {url}"), "shortened_or_raw_link")
    assert f["severity"] == "medium"


@pytest.mark.parametrize("url", ["https://www.irs.gov/payments", "https://www.onlinesbi.sbi", "www.amazon.in/orders"])
def test_shortened_link_negative(check, url):
    assert "shortened_or_raw_link" not in rules_of(check(f"Details: {url}"))


def test_shortened_link_alone_is_not_a_scam(check):
    assert check("Our new store opens Monday. Map: https://bit.ly/3xyz")["verdict"] != "likely_scam"


# ---------------------------------------------------------------- kyc_update_threat

def test_kyc_threat_strong_with_link(check):
    result = check("Dear Customer, Your SBI Account will be blocked today. Update your PAN Card Number, click here "
                   "https://tinyurl.com/2v5bn795")
    assert flag(result, "kyc_update_threat")["severity"] == "strong"
    assert result["verdict"] == "likely_scam"


def test_kyc_threat_strong_with_personal_mobile(check):
    result = check("NOTICE\nDear Customer, your SIM KYC has been suspended. Your SIM card will be blocked within "
                   "24 hours. Call KYC executive: 8961216971")
    assert flag(result, "kyc_update_threat")["severity"] == "strong"
    assert result["verdict"] == "likely_scam"


def test_kyc_threat_medium_without_link_or_number(check):
    result = check("Dear Customer, your KYC is pending and your account will be restricted. Please update it.")
    assert flag(result, "kyc_update_threat")["severity"] == "medium"


@pytest.mark.parametrize("text", [
    "Dear Customer, KYC for your SBI account is due. Please visit your home branch with your documents. -SBI",
    "Never share your OTP. Banks do not block accounts over SMS for KYC. -SBI",
    ITD_HEADER + "Name: RAVI KUMAR  PAN: ABCPX1234X\nYour return has been processed.",
])
def test_kyc_threat_negative(check, text):
    assert "kyc_update_threat" not in rules_of(check(text))


# ---------------------------------------------------------------- prize_or_refund_bait

@pytest.mark.parametrize("text", [
    "CONGRATULATION : YOU ARE THE WINNER OF 25,00,000 RS IN KBC LOTTERY",
    "Your CV has been selected for a daily salary of Rs 9500.",
    "You are entitled to an overdue refund of 41,104.22 rs, please input your correct details and proceed.",
    "Pre-approved loan of Rs 5,00,000 at 2% interest for you.",
    "प्रधानमंत्री योजना आधारकार्ड लोन 2% ब्याज, 50% माफ",
])
def test_bait_positive(check, text):
    assert "prize_or_refund_bait" in rules_of(check(text))


def test_bait_strong_when_claimed_through_whatsapp(check):
    result = check("Your CV has been selected for a daily salary of Rs 9500, contact: http://wa.me/639198720373")
    assert flag(result, "prize_or_refund_bait")["severity"] == "strong"
    assert result["verdict"] == "likely_scam"


def test_bait_medium_without_unofficial_channel(check):
    result = check("You have won a lucky draw prize. Visit our store to collect it.")
    assert flag(result, "prize_or_refund_bait")["severity"] == "medium"


@pytest.mark.parametrize("text", [
    IRS_HEADER + "You may be eligible for a refund of up to $496. Please complete the worksheet on page 3.",
    IRS_HEADER + "We're holding your refund until we finish reviewing your tax return.",
    ITD_HEADER + "A refund of Rs. 7,861 has been determined and will be credited to your bank account.",
    IRS_HEADER + "If you don't have to file a tax return, you won't need to use your IP PIN.",
    "We are pleased to offer you the position of Analyst. Your salary will be Rs 6,00,000 a year.",
])
def test_bait_negative(check, text):
    assert "prize_or_refund_bait" not in rules_of(check(text))


# ---------------------------------------------------------------- unexpected_fee_to_release

@pytest.mark.parametrize("text", [
    "YOU ARE SELECTED AS WINNER OF 25,00,000 RS. KBC REGISTRATION CHARGES: 6,500",
    "Your job is confirmed. Pay the registration fee of Rs 2,000 to receive your welcome kit.",
    "Your refund is ready. A processing fee of $49 must be paid before release.",
])
def test_fee_to_release_strong(check, text):
    f = flag(check(text), "unexpected_fee_to_release")
    assert f["severity"] == "strong"


def test_fee_for_parcel_is_medium(check):
    f = flag(check("Your parcel is held at the depot. Pay a redelivery fee of £1.45 to release it."),
             "unexpected_fee_to_release")
    assert f["severity"] == "medium"


@pytest.mark.parametrize("text", [
    IRS_HEADER + "You can also pay by debit or credit card for a small fee. Visit www.irs.gov/payments.",
    "Real prizes never require a processing fee. You have won nothing and owe nothing.",
    "Refund of processing fee: Rs 500 has been credited to your loan account.",
    "Loan sanction letter. Processing fee: 1% of the loan amount.",
])
def test_fee_to_release_negative(check, text):
    assert "unexpected_fee_to_release" not in rules_of(check(text))


# ---------------------------------------------------------------- press_to_connect

@pytest.mark.parametrize("text", [
    "This is the Social Security Administration. Press 1 to speak to an officer.",
    "Your Amazon account will be charged $1,499. Press 9 now.",
    "Press 9 or call 07000 012345 to speak to the TRAI officer.",
])
def test_press_positive(check, text):
    assert flag(check(text), "press_to_connect")["severity"] == "medium"


@pytest.mark.parametrize("text", [
    "For English press 1. Para español oprima 2.",
    "Call 800-829-1040 and press 2 for account questions.",
    "Press the Submit button on the form to finish.",
])
def test_press_negative(check, text):
    assert "press_to_connect" not in rules_of(check(text))


# ---------------------------------------------------------------- callback_unofficial

def test_callback_personal_mobile_with_disconnection_is_strong(check):
    result = check("Dear Consumer Your Electricity power will be disconnected. Tonight at 9.30 pm from electricity "
                   "office. Please immediately contact with our electricity officer 7074897254 Thank you.")
    assert flag(result, "callback_unofficial")["severity"] == "strong"
    assert result["verdict"] == "likely_scam"


def test_callback_landline_with_cutoff_tonight_is_strong(check):
    result = check("Your electricity power connection will be Disconnected tonight 09:00 pm.\n"
                   "To update your bill call our helpline number:-\n0824-060-6707")
    assert flag(result, "callback_unofficial")["severity"] == "strong"


def test_callback_fake_invoice_is_medium(check):
    result = check("Your have sent a payment of 497 USD. If you did not make this transaction, please contact "
                   "PayPal at +1 (801) 317-8874 to cancel.")
    assert flag(result, "callback_unofficial")["severity"] == "medium"


@pytest.mark.parametrize("text", [
    IRS_HEADER + "If you disagree, call us at 800-829-1040.",
    "Acme Water Co-op\nQuestions about your statement? Call 1-888-555-0199.",
    "Rs 5,000 debited from A/c XX1234. If you did not make this transaction, call 1800 425 3800. -SBI",
    "BSES Rajdhani Power Limited\nSupply to your area will be off for maintenance. Call 19123.",
])
def test_callback_not_strong_for_ordinary_numbers(check, text):
    result = check(text)
    assert all(f["severity"] != "strong" for f in result["flags"] if f["rule"] == "callback_unofficial")
    assert result["verdict"] != "likely_scam"


def test_callback_official_number_passes(check):
    result = check(IRS_HEADER + "Your account will be suspended today unless you call 800-829-1040.")
    assert "callback_unofficial" not in rules_of(result)


# ---------------------------------------------------------------- impersonation_mismatch

def test_impersonation_registry_agency_with_no_official_contact(check):
    result = check(IRS_HEADER + "Questions? Call 1-888-555-0199.")
    f = flag(result, "impersonation_mismatch")
    assert f["severity"] == "medium"
    assert result["verdict"] == "cant_tell"


def test_impersonation_strong_with_link_request(check):
    result = check(ITD_HEADER + "You are entitled to a refund of Rs 41,104. Claim it at https://itd-refunds.co/claim "
                                "or call 98100 12345.")
    assert flag(result, "impersonation_mismatch")["severity"] == "strong"
    assert result["verdict"] == "likely_scam"


def test_impersonation_email_sender_domain(check):
    result = check("From: Companies House <service.online-identification@ezybizz.com>\n"
                   "Subject: Action required\nWe have not received your identification. Please identify yourself "
                   "online and enter your required information.")
    f = flag(result, "impersonation_mismatch")
    assert f["severity"] == "strong"
    assert "ezybizz.com" in f["why"]


def test_impersonation_freemail_sender_even_when_local_part_unreadable(check):
    result = check("From: Companies House [mailto: […]@gmail.com]\nVerify your identity for Companies House.")
    assert flag(result, "impersonation_mismatch")["severity"] == "strong"


@pytest.mark.parametrize("text", [
    "From: Companies House <noreply@companieshouse.gov.uk>\nPlease verify your identity by your due date.",
    "From: IRS <irs@service.govdelivery.com>\nTax tips for this filing season.",
    "From: Acme Stores <deals@acme-mail.com>\nPlease confirm your account details.",
    IRS_HEADER + "Call 800-829-1040 or visit www.irs.gov.",
])
def test_impersonation_negative(check, text):
    assert "impersonation_mismatch" not in rules_of(check(text))


def test_bare_gov_uk_branding_does_not_confirm_hmrc(check):
    """A "GOV.UK" logo line is copied by scam emails; it is not an official contact."""
    result = check("GOV.UK\nHM Revenue & Customs\nYour tax account statement is ready.", source="textract")
    assert result["verdict"] != "consistent_with_genuine"


# ---------------------------------------------------------------- existing rules tightened

def test_custody_needs_police_sense(check):
    assert "threat_arrest" not in rules_of(check("We would like to invest US $500,000 under your custody."))
    assert "threat_arrest" in rules_of(check("You will be taken into custody if you do not pay."))


def test_maintain_confidentiality_is_secrecy(check):
    assert "secrecy" in rules_of(check("Please you have to maintain absolute confidentiality as regards this deal."))
    assert "secrecy" not in rules_of(check("We maintain strict confidentiality of your data."))


def test_model_credential_quote_needs_a_real_secret(check):
    ex = {"credential_requests": [{"quote": "When you file your federal tax return, enter the IP PIN in the correct "
                                            "place:"}]}
    result = check(IRS_HEADER + "When you file your federal tax return, enter the IP PIN in the correct place:", ex)
    assert "credential_request" not in rules_of(result)


def test_model_threat_quote_advising_police_report_is_ignored(check):
    ex = {"threats": [{"quote": "Report fraudulent activity to your local police or sheriff's department"}]}
    result = check(IRS_HEADER + "Report fraudulent activity to your local police or sheriff's department.", ex)
    assert "threat_arrest" not in rules_of(result)


# ---------------------------------------------------------------- model fields

def test_record_letter_tool_has_evidence_lists():
    import pipeline
    props = pipeline.record_letter_tool(["irs"])["inputSchema"]["json"]["properties"]
    for key in ("link_requests", "callback_requests", "account_verification_requests", "prize_or_refund_bait"):
        assert props[key]["items"]["properties"]["quote"]["type"] == "string"


def test_normalize_keeps_new_evidence_lists():
    import verifier
    ex = verifier.normalize_extraction({"callback_requests": ["Call 98100 12345 now"], "prize_or_refund_bait": 7})
    assert ex["callback_requests"] == [{"quote": "Call 98100 12345 now"}]
    assert ex["prize_or_refund_bait"] == [] and ex["link_requests"] == []


def test_model_bait_quote_counts_medium_when_grounded(check):
    ex = {"prize_or_refund_bait": [{"quote": "Collect your free gift hamper at the store"}]}
    result = check("Acme Stores\nCollect your free gift hamper at the store", ex)
    f = flag(result, "prize_or_refund_bait")
    assert f["severity"] == "medium" and f["grounded"] is True
    assert "Reported by the model" in trace_step(result, "rule:prize_or_refund_bait")["detail"]


def test_hindi_prize_wording_is_found_in_code(check):
    assert "prize_or_refund_bait" in rules_of(check("सूचना\nआपको इनाम मिला है"))
