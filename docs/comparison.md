# How Plainly compares with Norton Genie and Bitdefender Scamio

Norton Genie and Bitdefender Scamio are the two consumer scam checkers people are most likely to have heard of. Both take a message or a screenshot and say whether it looks like a scam. Plainly overlaps with them on that first step and then goes somewhere they don't: it is built for official mail, and a letter that checks out gets deadlines and a reply draft.

Pages checked on 30 Sep 2026. Where a vendor page did not say something, the table says "not stated" instead of guessing.

## What each one does

| | Norton Genie | Bitdefender Scamio | Plainly |
|---|---|---|---|
| What you give it | Emails, text messages, links, images and other messages (Gen Digital release) | Typed descriptions, pasted messages, links, QR codes, screenshots and images (Scamio page) | A photo, PDF or screenshot of a letter, SMS or email, or pasted text |
| Where it runs | Norton app, and as an app inside ChatGPT since 4 Mar 2026 | Web chat, WhatsApp, Facebook Messenger, Discord | Mobile-first web page. No app, no account. |
| Sign-in | Not stated in the release | "sign in or create a Bitdefender account" | None |
| Price | Release says the ChatGPT app works on Free, Plus, Team and Enterprise tiers; no price given | Free ("Yes! Bitdefender Scamio is a free AI-powered scam detector") | Free |
| How it decides | "examines the language, intent, and tactics being used, alongside URL and domain checks" | Compares input with "a set of predefined rules and Bitdefender's huge database of known scams and phishing attempts" | The model pulls out quoted evidence. Python rules decide the verdict, and every quote is checked against Textract's independent OCR text. |
| What you get back | "guidance, explaining why something may be risky and what steps to take next" | "lets you know if it's safe or not", with recommendations | One of three verdicts, never "safe": Likely scam, Consistent with a genuine [agency] letter (confirm on the official number), or Can't tell. Each flag quotes the line it came from, and a receipts panel lists every check with pass, flag or unknown. |
| Official contacts | Not stated | Not stated | Registry of agency domains and phone numbers, each with its source URL and the date it was checked. A scam verdict shows the official number to call instead. |
| If the letter is genuine | Not stated | Not stated | Plain-language explanation, deadlines computed in code from the letter's own date, an `.ics` calendar file, and a reply draft |
| Languages | Not stated in the release | Not stated on the product page | Explanation in English, Hindi, Spanish, or any language typed into the "other" field |
| Data kept | Not stated in the release | Refers to Bitdefender's general privacy policy | Nothing. Letter text is held in memory for one request, and logs carry no letter text. |

## Where Plainly is different

- It is narrower on purpose. It checks messages that claim to come from an official body (tax, pensions, immigration, electricity, police, customs) against a registry of those bodies' real contacts, with a source for each entry.
- The model does not decide. It extracts quotes; code checks each quote against OCR text the model did not produce and then applies fixed rules. A strong flag whose quote cannot be found in the OCR text is downgraded and marked as not grounded.
- "Can't tell" is a real answer. An unknown phone number alone never produces "Likely scam", and nothing ever produces "safe". The best a letter can get is "consistent with genuine, confirm on the official number".
- It keeps going when the letter checks out. Most people with an official letter need to know what it says, what to do and by when. Plainly computes the deadline, hands over a calendar file and drafts the reply.
- It explains in the reader's language, for families handling official mail in a second language.
- It shows its work. The receipts panel lists every check, including the ones that passed.

## Where they are better

- Coverage. Genie and Scamio handle every kind of scam: shopping sites, romance, investment, fake delivery texts. Plainly only knows the agencies in its registry (14 today) and says "Can't tell" for the rest.
- Threat data. Bitdefender compares against its own database of known scams and phishing attempts, and Genie runs URL and domain checks. Plainly has no reputation feed and does not visit links.
- Reach. Scamio sits inside WhatsApp, Messenger and Discord, and Genie sits inside ChatGPT, where people already are. Plainly is a web page you have to open.
- Conversation. Both are chat assistants you can ask follow-up questions. Plainly gives one structured answer per letter.
- Maturity. Both come from security companies with years of scam data. Plainly is a hackathon build, evaluated on a small labeled set ({{EVAL_SUMMARY}}).

## Sources

- Gen Digital, "The World's First AI-Powered Scam Detector, Norton Genie, Now in ChatGPT", 4 Mar 2026: https://newsroom.gendigital.com/2026-03-04-The-Worlds-First-AI-Powered-Scam-Detector,-Norton-Genie,-Now-in-ChatGPT
- Norton product page (describes Genie as part of Norton's scam protection): https://us.norton.com/products/genie-scam-detector
- Bitdefender Scamio: https://www.bitdefender.com/en-us/consumer/scamio
