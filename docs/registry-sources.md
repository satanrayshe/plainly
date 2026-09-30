# Registry sources

Every fact in `backend/registry.json`, with the page it came from and a short verbatim quote so a person can
spot-check it in a few minutes. All pages were fetched on **2026-09-30** (`checked_on`).

How to spot-check: open the URL, Ctrl+F a few words of the quote. Line breaks on the page are shown as ` / `.

Basis column:
- **stated**: the agency says this in its own words ("we never ...", "X does not ...").
- **advice**: the page advises the public rather than describing the agency's own conduct, or the
  `never_does` wording in the registry is a close paraphrase of the quote. Worth a second look before it is shown
  as a hard rule.
- **redirect**: evidence is an HTTP redirect, not page text.

Fetch notes:
- ssa.gov, incometaxindia.gov.in, pib.gov.in and reportfraud.police.uk block the WebFetch tool (HTTP 403). Those
  pages were fetched with curl using normal browser headers and the quotes checked against that copy.
- TRAI press releases are PDFs; the text was extracted locally with pypdf (the scan has OCR quirks such as
  `faciLity`, kept verbatim).
- www.irs.gov/help/telephone-assistance redirects to www.irs.gov/help/let-us-help-you; the registry uses the latter.
- www.actionfraud.police.uk now redirects to www.reportfraud.police.uk, so the UK channel is recorded as
  "Report Fraud (formerly Action Fraud)". The phone number 0300 123 2040 is unchanged.
- Domains are registrable domains. `gov.uk` is shared by every UK department, so it is listed for HMRC and DVLA
  but only proves "UK government", not which department.


## Report channel: US

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Channel: ReportFraud.ftc.gov | <https://consumer.ftc.gov/articles/how-avoid-government-impersonation-scam> | "That’s a scam. Report it at ReportFraud.ftc.gov." | stated |

## Report channel: India

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Channel: 1930 / cybercrime.gov.in | <https://cbi.gov.in/press-detail/ODAzMg==> | "report the matter on the National Cyber Crime Helpline 1930 or at www.cybercrime.gov.in." | stated |

## Report channel: UK

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Channel: Report Fraud (police) | <https://www.reportfraud.police.uk/what-is-report-fraud> | "Report Fraud is the place to tell the police about cyber crime and fraud." | stated |
| Phone 0300 123 2040 | <https://www.reportfraud.police.uk/what-is-report-fraud> | "make a report online or by phone on 0300 123 2040." | stated |
| Former name Action Fraud | <https://www.actionfraud.police.uk/contact-us> | (no quote: actionfraud.police.uk/contact-us redirects to reportfraud.police.uk/contact-us) | redirect |

## Internal Revenue Service (US)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 800-829-1040 (Individuals) | <https://www.irs.gov/help/let-us-help-you> | "Individuals / 800-829-1040" | stated |
| Phone 800-829-4933 (Businesses) | <https://www.irs.gov/help/let-us-help-you> | "Businesses / 800-829-4933" | stated |
| Phone 844-545-5640 (TAC appointments) | <https://www.irs.gov/help/let-us-help-you> | "then call 844-545-5640 to schedule an appointment." | stated |
| Phone 800-829-4059 (TTY/TDD) | <https://www.irs.gov/help/let-us-help-you> | "TTY/TDD 800-829-4059" | stated |
| Domain irs.gov | <https://www.irs.gov/newsroom/holiday-scam-reminder-gift-cards-are-never-used-to-make-tax-payments> | "claiming to be from the IRS to phishing@irs.gov." | stated |
| Never: demand immediate payment by gift card etc. | <https://www.irs.gov/newsroom/holiday-scam-reminder-gift-cards-are-never-used-to-make-tax-payments> | "Call to demand immediate payment using a specific payment method such as a gift card, prepaid debit card" | stated |
| Never: accept gift cards | <https://www.irs.gov/newsroom/holiday-scam-reminder-gift-cards-are-never-used-to-make-tax-payments> | "the agency won't ask for or accept gift cards as payment for a tax bill." | stated |
| Never: deny question/appeal | <https://www.irs.gov/newsroom/holiday-scam-reminder-gift-cards-are-never-used-to-make-tax-payments> | "Demand that taxpayers pay taxes without the opportunity to question or appeal the amount they owe." | stated |
| Never: threaten arrest | <https://www.irs.gov/newsroom/holiday-scam-reminder-gift-cards-are-never-used-to-make-tax-payments> | "Threaten to bring in local police, immigration officers or other law enforcement to have the taxpayer arrested" | stated |
| Never: threaten licences/status | <https://www.irs.gov/newsroom/holiday-scam-reminder-gift-cards-are-never-used-to-make-tax-payments> | "Threaten to revoke the taxpayer's driver's license, business licenses or immigration status." | stated |

## Social Security Administration (US)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 1-800-772-1213 | <https://oig.ssa.gov/scam-alerts/2026-08-31-protect-your-social-security-number/> | "Call Social Security directly at 1-800-772-1213." | stated |
| Domain ssa.gov | <https://oig.ssa.gov/scam-alerts/2026-08-31-protect-your-social-security-number/> | "my Social Security account at https://www.ssa.gov/myaccount." | stated |
| Never: unexpected contact for info | <https://oig.ssa.gov/scam-alerts/2026-08-31-protect-your-social-security-number/> | "Contact you unexpectedly to ask for personal information or bank account details." | stated |
| Never: suspend SSN / seize account | <https://oig.ssa.gov/scam-alerts/2026-08-31-protect-your-social-security-number/> | "Threaten to suspend your SSN or seize your bank account." | stated |
| Never: move money to protect it | <https://oig.ssa.gov/scam-alerts/2026-08-31-protect-your-social-security-number/> | "Tell you to transfer or move your money to protect it." | stated |
| Never: gift cards, crypto, cash | <https://oig.ssa.gov/scam-alerts/2026-08-31-protect-your-social-security-number/> | "Demand payment by gift cards, gold, prepaid debit cards, payment apps, cryptocurrency, wire transfers, or cash." | stated |
| Never: secrecy | <https://oig.ssa.gov/scam-alerts/2026-08-31-protect-your-social-security-number/> | "Ask you to keep secrets." | stated |
| Never: info via social/email/text | <https://www.ssa.gov/scam/> | "Social Security will never ask for sensitive or personal information through social media, email, or text message." | stated |

## U.S. Citizenship and Immigration Services (US)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 800-375-5283, TTY 800-767-1833 | <https://www.uscis.gov/contactcenter> | "Our toll-free number is 800-375-5283 (TTY 800-767-1833)" | stated |
| Domain uscis.gov | <https://www.uscis.gov/scams-fraud-and-misconduct/avoid-scams/common-scams> | "USCIS may email you from a uscis.gov email address" | stated |
| Known fake: uscis-online.org | <https://www.uscis.gov/scams-fraud-and-misconduct/avoid-scams/common-scams> | "a fraudulent download button that links to a non-government web address (uscis-online.org)." | stated |
| Never: transfer money to individual | <https://www.uscis.gov/scams-fraud-and-misconduct/avoid-scams/common-scams> | "We will never ask you to transfer money to an individual." | stated |
| Never: Western Union ... gift cards | <https://www.uscis.gov/scams-fraud-and-misconduct/avoid-scams/common-scams> | "We do not accept Western Union, MoneyGram, PayPal, Venmo, or gift cards as payment for immigration fees." | stated |
| Never: pay a person by phone/email | <https://www.uscis.gov/scams-fraud-and-misconduct/avoid-scams/common-scams> | "we will never ask you to pay fees to a person on the phone or by email." | stated |
| Never: personal social media | <https://www.uscis.gov/scams-fraud-and-misconduct/avoid-scams/common-scams> | "will not contact you through your personal social media accounts" | stated |
| Never: routine approval emails | <https://www.uscis.gov/scams-fraud-and-misconduct/avoid-scams/common-scams> | "We do not routinely send emails to inform you that we have approved you for a diversity visa" | stated |

## Medicare (Centers for Medicare & Medicaid Services) (US)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 1-800-633-4227, TTY 1-877-486-2048 | <https://www.medicare.gov/basics/get-started-with-medicare/using-medicare/your-medicare-card> | "call us 1-800-MEDICARE (1-800-633-4227). TTY: 1-877-486-2048." | stated |
| Never: uninvited calls for info | <https://www.medicare.gov/basics/get-started-with-medicare/using-medicare/your-medicare-card> | "Medicare will never call you uninvited and ask you to give us personal or private information." | stated |
| Never: sell / home visits | <https://www.medicare.gov/basics/reporting-medicare-fraud-and-abuse> | "Medicare will never call you to sell you anything or visit you at your home." | stated |
| Never: threaten to cancel benefits | <https://www.medicare.gov/basics/get-started-with-medicare/using-medicare/your-medicare-card> | "If someone calls and asks for your information, for money, or threatens to cancel your health benefits, hang up" | advice |

## United States Postal Service (US)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 1-800-275-8777 | <https://www.usps.com/help/contact-us.htm> | "Call: 1-800-ASK-USPS® (1-800-275-8777)" | stated |
| Phone 1-800-222-1811 (tracking) | <https://www.usps.com/help/contact-us.htm> | "about another issue with your package, please call us. / 1-800-222-1811" | stated |
| Phone 1-877-876-2455 (USPIS) | <https://www.uspis.gov/news/scam-article/smishing-package-tracking-text-scams> | "Call:1-877-876-2455" | stated |
| Domain usps.gov | <https://www.usps.com/help/contact-us.htm> | "sfsdelivery.confirmation@usps.gov" | stated |
| Domain uspis.gov | <https://www.uspis.gov/news/scam-article/smishing-package-tracking-text-scams> | "To report USPS related smishing, send an email to spam@uspis.gov." | stated |
| Never: unrequested texts/emails | <https://www.uspis.gov/news/scam-article/smishing-package-tracking-text-scams> | "USPS will not send customers text messages or e-mails without a customer first requesting the service with a tracking number," | stated |
| Never: links in texts | <https://www.uspis.gov/news/scam-article/smishing-package-tracking-text-scams> | "and it will NOT contain a link." | stated |
| Never: charge for tracking | <https://www.uspis.gov/news/scam-article/smishing-package-tracking-text-scams> | "USPS does not charge for these services!" | stated |

## Income Tax Department (IN)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 1800 103 0025 (e-Filing and CPC) | <https://www.incometax.gov.in/iec/foportal/contact-us> | "08:00 hrs - 20:00 hrs (Monday to Friday) / 1800 103 0025" | stated |
| Phone 1800 419 0025 (same desk) | <https://www.incometax.gov.in/iec/foportal/contact-us> | "1800 419 0025" | stated |
| Phones +91-80-46122000 and +91-80-61464700 (same desk, from outside the toll-free network; added by the integrator on 2026-09-30) | <https://www.incometax.gov.in/iec/foportal/contact-us> | "1800 103 0025 (or) 1800 419 0025 +91-80-46122000 +91-80-61464700 08:00 hrs - 20:00 hrs" | stated |
| Phone 1800 309 0130 (Demand Facilitation Centre) | <https://www.incometax.gov.in/iec/foportal/contact-us> | "1800 309 0130 / +91 821 6671200" | stated |
| DFC outbound numbers call taxpayers | <https://www.incometax.gov.in/iec/foportal/contact-us> | "Outbound Numbers (Taxpayers will receive calls from Demand Facilitation Centre from numbers below)" | stated |
| Phone +91 8216671200 (DFC outbound) | <https://www.incometax.gov.in/iec/foportal/contact-us> | "+91 8216671200 / +91 821-7151515" | stated |
| Domain incometax.gov.in | <https://www.incometaxindia.gov.in/report-phishing> | "webmanager@incometax.gov.in" | stated |
| Never: personal info by email | <https://www.incometaxindia.gov.in/report-phishing> | "The Income Tax Department does not request detailed personal information through e-mail." | stated |
| Never: PINs/passwords by email | <https://www.incometaxindia.gov.in/report-phishing> | "does not send e-mail requesting your PIN numbers, passwords or similar access information" | stated |
| DIN on every communication | <https://www.incometax.gov.in/iec/foportal/help/authenticate-notice-faq> | "issued on or after 1st October, 2019 shall bear an unique Document Identification Number(DIN)." | stated |
| No DIN = invalid | <https://www.incometax.gov.in/iec/foportal/help/authenticate-notice-faq> | "the notice/order/letter received by you would be treated as invalid" | stated |

## Unique Identification Authority of India (Aadhaar) (IN)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 1947 | <https://uidai.gov.in/en/> | "Toll-free Number / 1947" | stated |
| Phone 1947 (PIB release) | <https://www.pib.gov.in/PressReleasePage.aspx?PRID=1887539> | "may contact UIDAI on toll-free helpline 1947 which is available 24x7" | stated |
| Domain uidai.gov.in | <https://www.pib.gov.in/PressReleasePage.aspx?PRID=1887539> | "email at help@uidai.gov.in" | stated |
| OTP (advice) | <https://www.pib.gov.in/PressReleasePage.aspx?PRID=1887539> | "Aadhaar holders should not disclose Aadhaar OTP to any unauthorized entity" | advice |
| mAadhaar PIN (advice) | <https://www.pib.gov.in/PressReleasePage.aspx?PRID=1887539> | "refrain from sharing m-Aahaar PIN with anyone." | advice |
| Aadhaar number alone can't empty an account | <https://uidai.gov.in/en/your-aadhaar> | "no one can withdraw money from Aadhaar linked bank account." | advice |

## Employees' Provident Fund Organisation (IN)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 14470 | <https://www.epfo.gov.in/contact-us/> | "Toll-Free Helpline: 14470" | stated |
| Phone 1800118005 | <https://passbook.epfindia.gov.in/MemberPassBook/login> | "Help Desk/Toll Free Number : 1800118005" | stated |
| Domain epfigms.gov.in | <https://www.epfo.gov.in/contact-us/> | "Register your grievance online through the official EPFiGMS Portal: https://epfigms.gov.in/" | stated |
| Domain epfindia.gov.in | <https://www.epfo.gov.in/contact-us/> | "rc.csd@epfindia.gov.in" | stated |
| Never: personal info over phone | <https://unifiedportal-mem.epfindia.gov.in/memberinterface/> | "EPFO never requests personal information such as Aadhaar, PAN, or bank details over the phone." | stated |
| Never: ask for deposits | <https://unifiedportal-mem.epfindia.gov.in/memberinterface/> | "EPFO does not contact members to ask for any monetary deposits." | stated |
| Never: ask pensioners to deposit | <https://passbook.epfindia.gov.in/MemberPassBook/login> | "EPFO never calls members/pensioners to deposit any amount." | stated |
| OTP on a call (advice) | <https://passbook.epfindia.gov.in/MemberPassBook/login> | "Please never respond to any call for sharing any personal details like Aadhaar, PAN, Bank details, OTP" | advice |

## e-Challan (Parivahan traffic challans) (IN)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 0120-4925505 | <https://echallan.parivahan.gov.in/index/accused-challan> | "OR Phone : 0120-4925505 (Timings : 6:00 AM - 10:00 PM)" | stated |
| Never: password/OTP/payment details | <https://echallan.parivahan.gov.in/index/accused-challan> | "We never request your password, OTP, payment details or sensitive personal information via calls, emails, or messages or links." | stated |
| Only the official portal/app | <https://echallan.parivahan.gov.in/index/accused-challan> | "Access our portal only through this official website/app." | advice |

## India Post (IN)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 1800 266 6868 | <https://www.indiapost.gov.in/contactus> | "Customer Care Toll Free Number 1800 266 6868" | stated |
| Only indiapost.gov.in; fake indund.cyou | <https://www.indiapost.gov.in/> | "including indund.cyou. Please use only the official India Post website www.indiapost.gov.in" | advice |
| OTP/banking/card/UPI via links (advice) | <https://www.indiapost.gov.in/> | "do not share OTP, banking, card, UPI or other personal/financial information through unauthorized links." | advice |

## Telecom Regulatory Authority of India / Department of Telecommunications (IN)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Never: disconnection contact | <https://www.trai.gov.in/sites/default/files/2025-08/PR_No.71of2025.pdf> | "does not initiate communication with customers regarding mobile number disconnection through messages or otherwise." | stated |
| Never: third-party agencies | <https://www.trai.gov.in/sites/default/files/2025-04/PR_No.22of2025.pdf> | "TRAI has also not authorized any third-party Agency to contact Customers for such purposes." | stated |
| Never: investigate consumers | <https://www.trai.gov.in/sites/default/files/2025-08/PR_No.71of2025.pdf> | "TRAI does not: / Conduct investigations against individual consumers" | stated |
| Never: Aadhaar/bank/OTP | <https://www.trai.gov.in/sites/default/files/2025-08/PR_No.71of2025.pdf> | "Request Aadhaar, bank account, OTP, or other personal details" | stated |
| Never: arrest threats | <https://www.trai.gov.in/sites/default/files/2025-08/PR_No.71of2025.pdf> | "Issue arrest threats or warnings via digital platforms" | stated |
| Disconnection is done by your telecom provider | <https://www.trai.gov.in/sites/default/files/2025-04/PR_No.22of2025.pdf> | "is done by the respective Telecom Service Provider (TSP)." | stated |
| Domain sancharsaathi.gov.in (DoT) | <https://www.trai.gov.in/sites/default/files/2025-04/PR_No.22of2025.pdf> | "Chakshu faciLity on the Department of Telecommunications Sanchar Saathi platform." | stated |

## Central Bureau of Investigation (IN)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Never: digital arrest | <https://cbi.gov.in/press-detail/ODAzMg==> | "no police, CBI or other government agency places any person under “digital arrest” or demands money" | stated |
| Settle cases for money = imposter | <https://cbi.gov.in/advisory> | "offer to 'settle complaints/cases' in exchange for money or favours." | advice |
| Never: validate remittances | <https://cbi.gov.in/advisory> | "CBI does not certify / validate any foreign remittance or transaction of funds." | stated |
| Phones 011-24362755, 011-24361273 | <https://cbi.gov.in/advisory> | "at Phone no.011-24362755, 011-24361273" | stated |
| Domain cbi.gov.in | <https://cbi.gov.in/advisory> | "complaints@cbi.gov.in" | stated |

## HM Revenue & Customs (UK)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 0300 200 3300 | <https://www.gov.uk/find-hmrc-contacts/income-tax-enquiries> | "Telephone: 0300 200 3300" | stated |
| Phone +44 135 535 9022 | <https://www.gov.uk/find-hmrc-contacts/income-tax-enquiries> | "Outside UK: +44 135 535 9022" | stated |
| Domain hmrc.gov.uk | <https://www.gov.uk/guidance/identify-hmrc-related-scam-phone-calls-emails-and-text-messages> | "email: phishing@hmrc.gov.uk then delete them." | stated |
| Never: voicemail threats / arrest | <https://www.gov.uk/guidance/identify-hmrc-related-scam-phone-calls-emails-and-text-messages> | "HMRC will never: / leave a voicemail threatening legal action / threaten arrest" | stated |
| Never: gift vouchers | <https://www.gov.uk/guidance/identify-hmrc-related-scam-phone-calls-emails-and-text-messages> | "HMRC will never ask you to pay with gift or payment vouchers." | stated |
| Never: WhatsApp (except channel alerts) | <https://www.gov.uk/guidance/identify-hmrc-related-scam-phone-calls-emails-and-text-messages> | "HMRC will not communicate with you for any other reason using WhatsApp." | stated |

## Driver and Vehicle Licensing Agency (UK)

| Fact | Source | Quote | Basis |
|---|---|---|---|
| Phone 0300 790 6801 | <https://www.gov.uk/contact-the-dvla/y/driving-licences-and-applications> | "Telephone: 0300 790 6801" | stated |
| Phone 0300 790 6802 | <https://www.gov.uk/contact-the-dvla/y/vehicle-tax-and-sorn> | "Telephone: 0300 790 6802" | stated |
| Domain dvla.gov.uk | <https://www.gov.uk/government/news/7-tips-for-motorists-to-stay-safe-online> | "Email press.office@dvla.gov.uk" | stated |
| GOV.UK is the only trusted source | <https://www.gov.uk/government/news/dvla-warns-motorists-to-be-aware-of-scams> | "The only trusted source of DVLA information is GOV.UK." | stated |
| Never: emails asking for details | <https://www.gov.uk/government/news/7-tips-for-motorists-to-stay-safe-online> | "We never send emails that ask you to confirm your personal details or payment information." | stated |
| Never: refund texts | <https://www.gov.uk/government/news/7-tips-for-motorists-to-stay-safe-online> | "We never send texts about vehicle tax refunds." | stated |
| Never: bank/card details by text/email | <https://www.gov.uk/government/news/dvla-releases-latest-scam-images-to-help-keep-motorists-safe-online> | "We never ask for bank or credit card details by text message or email," | stated |
| Never: ask you to claim refunds | <https://www.gov.uk/government/news/dvla-warns-motorists-to-be-aware-of-scams> | "we don’t ask for anyone to get in touch with us to claim their refund." | stated |
| Only 0300 numbers | <https://www.gov.uk/government/news/7-tips-for-motorists-to-stay-safe-online> | "Our contact centre numbers will only ever begin with 0300" | stated |

## Not included, and why

- **Customs (CBIC)**: cbic.gov.in is a JavaScript app with no fetchable text for scam advisories or a helpline, so
  no Customs entry was added. Customs-parcel "digital arrest" letters are still covered by the CBI statement that
  no police, CBI or other government agency places anyone under digital arrest.
- **TRAI phone numbers**: TRAI's advisories tell people to check with their own telecom provider, and no TRAI
  number for the public was confirmed, so the entry has an empty `phones` list on purpose.
- **dot.gov.in**: the page renders only through JavaScript, so the domain could not be confirmed from page text
  and was left out. `sancharsaathi.gov.in` (DoT) is included, sourced from the TRAI press release.
- **SSA TTY and other secondary numbers**: not visible on a page that could be fetched, so omitted.
- **cms.gov** (Medicare's parent agency) and generic aliases such as CMS, DoT, ITD: left out on purpose. The
  lookalike rule treats official domain labels and short aliases as brand words, so "cms" or "dot" inside an
  unrelated address (cms.example.com) would be flagged as an imitation.
