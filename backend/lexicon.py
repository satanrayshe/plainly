"""Regex lexicon for the verifier rules: English as written in US, UK and Indian letters, plus cheap Hindi terms.

English alternatives carry their own \\b anchors; Devanagari ones do not, because vowel signs are not \\w and
word boundaries misbehave around them.
"""
import re

_I = re.IGNORECASE

GIFT_CARD = re.compile(
    r"\bgift\s*(?:cards?|vouchers?|codes?)\b|\bi\s?tunes\b"
    r"|\bgoogle\s*play\s*(?:gift\s*)?(?:cards?|codes?|vouchers?|recharge)\b"
    r"|\bsteam\s*(?:wallet|gift|cards?)\b|\bamazon\s*(?:pay\s*)?(?:gift\s*)?(?:cards?|vouchers?|codes?)\b"
    r"|\bapple\s*(?:gift\s*)?cards?\b|\be-?bay\s*cards?\b|\bvanilla\s*(?:visa|cards?|gift)\b"
    r"|\bprepaid\s*(?:cards?|vouchers?)\b|\bredemption\s+codes?\b|गिफ्ट\s*कार्ड",
    _I,
)

CRYPTO_WIRE = re.compile(
    r"\bbitcoins?\b|\bbtc\b|\bcrypto(?:currency|currencies)?\b|\busdt\b|\btether\b|\bethereum\b"
    r"|\b(?:bitcoin|crypto|btc)\s*atm\b|\bwire\s*transfers?\b|\bwire\s+(?:the\s+)?(?:money|funds|amount|payment)\b"
    r"|\bwestern\s*union\b|\bmoney\s*gram\b|\b(?:safe|secure|secret)\s+(?:bank\s+)?account\b"
    r"|\brbi\s+(?:verification\s+|safe\s+|escrow\s+)?account\b|बिटकॉइन|क्रिप्टो",
    _I,
)

UPI_CONTEXT = re.compile(r"\bupi\b|\bvpa\b|\bphone\s*pe\b|\bg\s?pay\b|\bgoogle\s*pay\b|\bpaytm\b|\bbhim\b"
                         r"|\bscan\b|\bqr\b|फोनपे|पेटीएम|यूपीआई", _I)
_PAYMENT_APP = r"(?:\bphone\s*pe\b|\bg\s?pay\b|\bgoogle\s*pay\b|\bpaytm\b|\bbhim\b|\bupi\b|फोनपे|पेटीएम|यूपीआई)"
_MOBILE = r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
# Only connecting words may sit between the app and the number ("PhonePe to 98100 12345", "GPay on +91 ..."), so
# "Pay via Paytm or Google Pay, WhatsApp 87459 99808 for a bill copy" is two separate things.
_APP_LINK = r"[\s:(\-/]*(?:(?:to|on|at|number|no\.?|mobile|id|via|by|through|using|पर|को|नंबर)[\s:(\-/]+)*"
PAYMENT_APP_TO_MOBILE = re.compile(rf"{_PAYMENT_APP}{_APP_LINK}{_MOBILE}|{_MOBILE}{_APP_LINK}{_PAYMENT_APP}", _I)
PAY_VERB = re.compile(r"\b(?:pay|paid|payment|send|transfer|deposit|remit|clear)\b|भुगतान|भेज|जमा", _I)
# Words that say what kind of sender it is, not who. They never mark a UPI handle as the sender's own.
GENERIC_NAME_WORDS = {
    "limited", "private", "power", "electricity", "electric", "energy", "bill", "bills", "notice", "final",
    "department", "government", "india", "indian", "office", "services", "service", "company", "corporation",
    "board", "water", "supply", "distribution", "authority", "ministry", "bank", "dear", "customer", "consumer",
    "sample", "date", "your", "account", "payment", "from", "with", "this", "that", "urgent", "alert", "text",
    "message", "disconnection", "reminder", "state", "national", "central", "public", "municipal", "city",
}
UPI_PROVIDERS = {
    "okaxis", "okhdfcbank", "okicici", "oksbi", "ybl", "ibl", "axl", "paytm", "ptyes", "ptaxis", "pthdfc", "ptsbi",
    "upi", "apl", "yapl", "rapl", "jio", "fam", "axisbank", "icici", "sbi", "hdfcbank", "kotak", "idfcbank", "axisb",
    "fbl", "freecharge", "airtel", "pingpay", "waicici", "wahdfcbank", "waaxis", "wasbi", "abfspay", "naviaxis",
    "superyes", "yesbank", "barodampay", "unionbank", "pnb", "cnrb", "boi", "indus", "federal", "kbl", "aubank",
    "rbl", "idbi", "ikwik", "mahb", "kvb", "cub", "uco", "psb", "indianbank", "iob", "centralbank", "dcb", "equitas",
}

CREDENTIAL = (
    r"\bOTP\b|\bone[\s-]?time[\s-]?(?:password|pin|passcode|code)\b"
    r"|\b(?:UPI|ATM|M|T|card|debit\s+card|credit\s+card|secret|net\s?banking)[\s-]?PIN\b"
    r"|(?<!IP\s)(?<!Protection\s)\bPIN\b(?!\s*(?:code|:?\s*\d{6}))"  # an IRS IP PIN goes on your own return
    r"|\bpass\s?words?\b|\bpass\s?code\b|\bCVV\b|\bCVC\b|\bcard\s+verification\b"
    r"|\b(?:full|complete|entire|whole)\s+(?:SSN|social\s+security\s+(?:number|no))\b|\ball\s+9\s+digits\b"
    r"|\b(?:full|complete|entire|whole|12[\s-]digit)\s+aadhaa?r\b"
    r"|\bnet[\s-]?banking\s+(?:login|user\s*(?:name|id)|password|credentials|details)\b"
    r"|\blog\s?in\s+(?:credentials|details)\b|ओटीपी|पिन|पासवर्ड|सीवीवी"
)
# Verbs that hand a secret over to whoever sent the letter.
HANDOVER_VERB = (
    r"\b(?:share|send|provide|tell|give|reply(?:\s+with)?|forward|read\s+out|read\s+back|disclose|mention|"
    r"note\s+down|dictate|spell\s+out)\b"
    r"|बताएं|बताइए|बताओ|बताना|भेजें|भेजिए|भेजो|शेयर\s*करें|शेयर\s*कीजिए|साझा\s*करें|दीजिए"
)
# Verbs that also describe signing in to an official portal yourself ("log in to incometax.gov.in and enter the
# OTP"). They only count when the sentence names no official site. "e-verify" is India's return process.
ENTRY_VERB = r"\b(?:confirm|enter|(?<![-\w])verify|update|submit|type)\b"
ENTRY_VERB_WORD = re.compile(ENTRY_VERB, _I)
CREDENTIAL_REQUEST = re.compile(
    rf"(?P<verb>{HANDOVER_VERB}|{ENTRY_VERB})(?:[^.\n।?!]|\.(?=\S)){{0,60}}?(?P<cred>{CREDENTIAL})"
    rf"|(?P<cred2>{CREDENTIAL})(?:[^.\n।?!]|\.(?=\S)){{0,30}}?(?P<verb2>{HANDOVER_VERB})",
    _I,
)
OFFICIAL_PORTAL = re.compile(r"\bportal\b|\bonline\s+account\b|\be-?filing\b|\bofficial\s+(?:website|site|app)\b", _I)
# Negation governing the request verb: "never share", "do not ever share", "will never ask you to share",
# "no one from the IRS will ask you to share", "न बताएं". Only these filler words may sit in between, so
# "do not disconnect and share the OTP" still counts as a request.
VERB_NEGATION = re.compile(
    r"(?:\bnever|\bnot|n't|\bno\s+one|\bnobody|न|मत|नहीं|कभी)\s*"
    r"(?:(?:ever|ask|asks|asked|request|requests|requested|require|requires|required|want|wants|expect|need|"
    r"you|to|be|will|would|anyone|us|them|for|from|the|our|staff|officer|officers|call|email|text|contact|"
    r"(?-i:[A-Z]{2,6}))\s+){0,7}$",
    _I,
)

THREAT = re.compile(
    r"\barrest(?:ed|ing)?\b|\bdigital\s+arrest\b|\bwarrants?\b|\bdeport(?:ed|ation)?\b|(?-i:\bFIR\b)"
    r"|\b(?:registered|filed|lodged|booked)\s+(?:a\s+)?(?:criminal\s+)?(?:case|complaint)\s+against\s+you\b"
    r"|\bjail(?:ed)?\b|\bprison\b|\bimprison(?:ment|ed)?\b|\b(?:police|judicial|taken\s+into|in(?:to)?|under)\s+custody\b|\bnarcotics\b|\bmoney\s+laundering\b"
    r"|\bdrugs?\s+(?:were|was|have\s+been|has\s+been)\s+(?:found|seized)\b"
    r"|(?-i:\bCBI\b)\s+(?:\w+\s+){0,3}?(?:case|investigation|inquiry|custody|arrest|officer)"
    # passport "police verification" (an officer visits to confirm your address) is a routine service step
    r"|\bpolice\s+(?!verification\b)(?:\w+\s+){0,3}?(?:arrest|come|visit|raid|case|complaint|custody|action)"
    r"|\b(?:report|hand(?:ed)?\s+over|forward(?:ed)?|refer(?:red)?)\s+(?:\w+\s+){0,3}?to\s+(?:the\s+)?"
    r"(?:police|cyber\s*cell|court|CBI|narcotics)\b(?!\s+(?:station\s+)?for\s+(?:\w+\s+)?verification\b)"
    r"|\blegal\s+action\b[^.\n]{0,50}?(?:\btoday\b|\bimmediately\b|\btonight\b|\bwithin\s+\d+\s+hours?\b|\bat\s+once\b)"
    r"|(?:\btoday\b|\bimmediately\b|\btonight\b|\bwithin\s+\d+\s+hours?\b)[^.\n]{0,50}?\blegal\s+action\b"
    r"|गिरफ्तार|गिरफ़्तार|डिजिटल\s*अरेस्ट|वारंट|जेल|हिरासत|एफ\s*आई\s*आर|सीबीआई|पुलिस\s*(?:केस|कार्रवाई|कार्यवाही|थाने)"
    r"|कानूनी\s*कार्रवाई",
    _I,
)

VIDEO_CALL = re.compile(
    r"\bvideo[\s-]*call(?:s|ing)?\b|\bvideo\s+conference\b|\bskype\b|\bzoom\s+(?:call|meeting)\b"
    r"|\bwhats\s*app\s+video\b|वीडियो\s*कॉल",
    _I,
)
STAY_ON_CALL = re.compile(
    r"\bstay\s+on\s+(?:the\s+)?(?:call|line|video)\b|\b(?:do\s+not|don'?t|never)\s+(?:disconnect|end|cut|hang\s+up)"
    r"(?:\s+(?:the|this))?\s+(?:call|line|video)\b|\bkeep\s+(?:your\s+)?(?:camera|video)\s+(?:on|switched\s+on)\b"
    r"|\bremain\s+on\s+(?:the\s+)?(?:call|line|camera)\b|कॉल\s*(?:न|मत)\s*काट",
    _I,
)
VIDEO_KYC = re.compile(r"\bv-?kyc\b|\bvideo\s*kyc\b|\bkyc\b", _I)

URGENCY = re.compile(
    r"\bwithin\s+(?:the\s+next\s+)?(?P<hours>\d{1,2})\s*(?:hours?|hrs?)\b|(?P<hours_hi>\d{1,2})\s*घंटे"
    r"|\bwithin\s+(?:1|2|one|two)\s+days?\b|\bwithin\s+(?:the\s+)?hour\b"
    r"|\btonight\b|\bsame\s+day\b|\bby\s+end\s+of\s+(?:the\s+)?day\b|\bbefore\s+\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s+today\b"
    r"|\b(?:pay|call|respond|contact|act|clear|settle|update|verify|complete|visit|reply)\b[^.\n]{0,40}?\btoday\b"
    r"|\btoday\b[^.\n]{0,40}?(?:disconnect|suspend|block|cancel|arrest|legal|terminat|deactivat|cut\s+off)"
    r"|\b(?:disconnect|suspend|block|cancel|expire|deactivat|terminat|charged|debited)\w*[^.\n]{0,20}?\btoday\b"
    r"|आज\s*(?:ही|रात)",
    _I,
)
# "Immediately" is only urgent when the letter gives no real deadline; genuine notices often have a
# "What you need to do immediately" heading above a date weeks away.
SOFT_URGENCY = re.compile(
    r"\bimmediately\b|\bimmediate\s+(?:action|payment)\b|\bright\s+away\b|\bat\s+once\b|\bas\s+soon\s+as\s+possible\b"
    r"|\burgently\b|तुरंत|फौरन",
    _I,
)

SECRECY = re.compile(
    r"\b(?:do\s+not|don'?t|never)\s+(?:tell|inform|discuss\s+(?:this\s+)?with|mention\s+this\s+to|contact)\s+"
    r"(?:anyone|anybody|any\s+one|your\s+\w+|family|relatives|friends|the\s+bank|bank|police|others|local\s+police)"
    r"|\b(?:do\s+not|don'?t)\s+(?:share|disclose)\s+(?:this|the)\s+(?:matter|case|information|call|conversation|"
    r"investigation|notice)\b"
    r"|\bkeep\s+(?:this|it|the\s+matter|the\s+case|this\s+matter|this\s+call)?\s*(?:strictly\s+)?"
    r"(?:confidential|secret|private|between\s+us)\b"
    r"|\bwithout\s+(?:telling|informing)\b|\b(?:strictly|highly)\s+confidential\s+(?:matter|investigation|case)\b"
    r"|\bconfidential\s+investigation\b|\bsecret\s+investigation\b"
    r"|\b(?:you\s+(?:have\s+to|must|should|are\s+to)|please)\s+maintain\s+(?:\w+\s+)?(?:confidentiality|secrecy)\b"
    r"|किसी\s*को\s*(?:भी\s*)?(?:न|मत)\s*बता|गोपनीय\s*रख|परिवार\s*को\s*(?:न|मत)",
    _I,
)
CREDENTIAL_WORD = re.compile(CREDENTIAL, _I)

AI_INSTRUCTION = re.compile(
    r"\bignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier|preceding|other|your)\s+"
    r"(?:instructions?|prompts?|messages?|rules?|directions?|guidelines?)\b"
    r"|\bdisregard\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier|other|your)\s+"
    r"(?:instructions?|prompts?|rules?|guidelines?)\b"
    r"|\bas\s+an?\s+(?:ai|a\.i\.|artificial\s+intelligence|llm|large\s+language\s+model|language\s+model|"
    r"ai\s+assistant)\b"
    r"|\b(?:note|message|instructions?)\s+(?:to|for)\s+(?:the\s+|any\s+)?(?:ai|a\.i\.|llm|assistant|model|chatbot|"
    r"scanner|classifier|automated\s+(?:system|reviewer|tool))s?\b"
    r"|\b(?:ai|llm|language\s+model|chatbot|classifier|automated\s+(?:system|review|reviewer|tool))s?\b\s*[,:]?\s*"
    r"(?:must|should|shall|reading\s+this|reviewing\s+this|processing\s+this|analy[sz]ing\s+this)\b"
    r"|\b(?:classify|mark|treat|label|report|flag|rate|consider|categori[sz]e|tag)\s+(?:this|the)\s+"
    r"(?:letter|message|notice|document|email|e-mail|mail|sms|text)?\s*as\s+(?:legit(?:imate)?|genuine|safe|"
    r"authentic|real|verified|trusted|official|not\s+(?:a\s+)?(?:scam|fraud|phishing|suspicious))\b"
    r"|\bsystem\s+prompt\b|\bdeveloper\s+mode\b|\bjailbreak\b"
    r"|\byou\s+are\s+now\s+(?:an?\s+|the\s+)?(?:\w+\s+)?(?:ai|assistant|language\s+model|chatbot|bot)\b"
    r"|\bnew\s+instructions?\s*:|<\s*/?\s*(?:system|assistant|im_start|im_end)\b|\[\s*(?:system|inst)\s*\]",
    _I,
)

GOVERNMENT_OR_UTILITY = re.compile(
    r"\bdepartment\b|\bdept\b|\bministry\b|\bgovernment\b|\bgovt\b|\bfederal\b|\bstate\s+of\b|\bpolice\b|\bcourt\b"
    r"|\bbureau\b|\bauthority\b|\bboard\b|\bmunicipal\b|\bcorporation\b|\belectricity\b|\belectric\b|\bpower\b"
    r"|\benergy\b|\bdiscom\b|\butilit(?:y|ies)\b|\bwater\b|\bgas\b|\btax\b|\brevenue\b|\bcustoms\b"
    r"|\bsocial\s+security\b|\badministration\b|\bagency\b|\bcommission\b|\bcouncil\b|\btreasury\b|\btrai\b"
    r"|\btelecom\b|\breserve\s+bank\b|\brbi\b|\bpost\s+office\b|\bindia\s+post\b|\bcourier\b"
    r"|\bcompanies\s+house\b|\bgov\.uk\b|\bdmv\b|\bmotor\s+vehicles\b|\byojana\b"
    r"|सरकार|विभाग|बिजली|मंत्रालय|पुलिस|न्यायालय|निगम|योजना|प्रधानमंत्री",
    _I,
)
ORGANISATION = re.compile(GOVERNMENT_OR_UTILITY.pattern + r"|\bbank\b|\blimited\b|\bltd\b|\binc\b|\bllc\b|\bplc\b"
                          r"|\bcompany\b|\bservices\b|\binsurance\b|\bofficer\b|\bofficial\b|बैंक", _I)

AMOUNT = re.compile(
    r"(?:US\s?\$|\$|₹|£|€|\bRs\.?|\bINR|\bUSD|\bGBP)\s?\d[\d,]*(?:\.\d{1,2})?"
    r"|\b\d[\d,]*(?:\.\d{1,2})?\s?(?:rupees|dollars|pounds|रुपये|रुपए)",
    _I,
)

NEGATION = re.compile(r"\bnever\b|\bnot\b|n't\b|\bno\b|\bnobody\b|\bno\s+one\b|कभी\s*नहीं|मत\b|नहीं", _I)
CONDITIONAL = re.compile(r"\bif\b|\bunless\b|\bwhether\b|अगर|यदि", _I)
# "Do not ignore this or police will arrest you": the negation does not cover what follows "or ...".
# A plain list ("gift cards or crypto") keeps the negation.
RESUMES = re.compile(r"\bor\s+(?:else|you|we|they|the\s+police|police|your|legal|action|arrest|face|be)\b"
                     r"|\botherwise\b|\belse\b|\bfailing\s+(?:which|this|that)\b|\bbut\b|\binstead\b"
                     r"|\band\s+(?:you|then|please)\b|वरना|नहीं\s*तो", _I)
# Hindi puts the negation after the verb, at the end of the clause: "वीडियो कॉल पर गिरफ्तार नहीं करते" (do not arrest
# over video call), "डिजिटल अरेस्ट जैसी कोई चीज़ नहीं होती" (there is no such thing as digital arrest). "नहीं तो"
# (otherwise) is not a negation.
HINDI_NEGATED_AFTER = re.compile(
    r"^[^।.!?\n,]{0,60}?\s(?:नहीं|न|मत)\s*(?:(?:करते|करता|करती|करें|करे|होती|होता|होते|देते|देता|मांगते|मांगता|मांगती)\s*)?"
    r"(?:हैं|है)?\s*(?:[।.!?\n,]|$)")
# "We will never ask/demand/accept ...": a negated verb like this covers the whole list after it, commas and all.
# A list of such verbs is one negated action: "officers never question or arrest anyone over a video call".
_PROTECTIVE = (r"(?:ask|demand|request|require|accept|take|threaten|contact|use|want|expect|need|seek|collect|question|"
               r"arrest|interrogate)(?:s|ed|ing)?\b")
PROTECTIVE_VERB = re.compile(rf"^\s*(?:\S+\s+){{0,3}}?{_PROTECTIVE}(?:\s*(?:,|/|\bor\b|\band\b)\s*{_PROTECTIVE})*", _I)
# Public warnings describe the scam in its own words ("Fraudsters may say a warrant has been issued and ask you to
# stay on the video call", "If you get a call saying the CBI will arrest you, it is a scam", "There is no such
# thing as a digital arrest"). A match in a sentence framed like this is reported, not demanded.
WARNING_FRAME = re.compile(
    r"\bfraudsters?\b|\bscammers?\b|\bpretend(?:s|ing)?\s+to\s+be\b|\bposing\s+as\b"
    r"|\bif\s+(?:you\s+)?(?:get|receive)\s+(?:a|an|any)\s+(?:\w+\s+)?(?:call|message|sms|text|e-?mail|whats\s*app)\b"
    r"[^.\n]{0,30}?\b(?:saying|says|that\s+says|claiming|asking|threatening)\b"
    r"|\b(?:it|this|that|these|such\s+\w+)\s+(?:is|are)\s+(?:always\s+)?(?:a\s+)?(?:scam|fraud|fake)s?\b"
    r"|\bno\s+such\s+thing\s+as\b"
    r"|\bif\s+(?:someone|somebody|anyone|a\s+caller)\s+(?:\w+\s+){0,3}?(?:threatens?|claims?|says?|demands?)\b"
    r"|\bbeware\s+of\b[^.!?\n]{0,40}?\b(?:scams?|frauds?|fraudsters?|fake\w*|digital\s+arrest)\b",
    _I,
)


# ---------------------------------------------------------------- links, lures and call-backs

# "Click here", "use the following link", "visit the link below", "open link", "scan the QR code", "click bit.ly/..".
LINK_CTA = re.compile(
    r"\b(?:click|tap|open|visit|follow|use|go\s+to|scan)\b[^.\n]{0,40}?"
    r"(?:\blinks?\b|\bhere\b|\bbutton\b|\bqr\s*code\b|https?\b|\bwww\.|\bvia\s*:"
    r"|\b[\w-]+\.(?:ly|gy|li|gd|me|app|link|co|com|in|net|org|info|xyz|top|site|online)\b)"
    r"|\blink\s+(?:below|above|given|provided)\b|\b(?:in|on)\s+this\s+link\b|\bthe\s+link\s*[-:]"
    r"|लिंक\s*पर\s*क्लिक|क्लिक\s*करें",
    _I,
)
# What the link is for: money to claim, a payment, or details to "verify" or "update" before a block.
LINK_PURPOSE = re.compile(
    r"\brefunds?\b|\bclaim\b|\bverif(?:y|ication)\b|\bconfirm\b|\bupdat(?:e|ed|ing)\b|\bkyc\b|\bpan\b|\baadhaa?r\b"
    r"|\bunblock\b|\breactivat\w*|\brestore\b|\brecover\b|\bpay(?:ment)?\b|\bsettle\b|\binvoice\b|\bfine\b|\btoll\b"
    r"|\bdetails\b|\binformation\b|\bidentity\b|\bidentification\b|\bwallet\b|\bprize\b|\breward\b|\bcredited\b"
    r"|\bbilling\b|\bdocument\b|\bbalance\b|\bblocked\b|\bsuspended\b|\bexpire\w*|\bunpaid\b|भुगतान|अपडेट|रिफंड",
    _I,
)
# A short button label on its own line in a pasted email: "Verify Your Identity Now", "Check Your Refund".
BUTTON_LINE = re.compile(
    r"^[ \t•*>-]*(?:verify|update|confirm|recover|restore|reactivate|unlock|unblock|claim|check|start|complete|"
    r"activate|secure)\b(?=[^\n.]*\b(?:verify|verification|update|confirm|recover|restore|reactivate|unlock|"
    r"unblock|claim|refund|kyc|wallet|identity)\b)[^\n.:]{0,40}$",
    _I | re.M,
)
# Phones switch off links in texts from strangers; replying or copying the link switches them back on.
LINK_BYPASS = re.compile(
    r"\breply\s+(?:with\s+)?[\"'“]?y[\"'”]?(?=[\s,.])[^\n]{0,80}?\b(?:link|re-?open|open\s+it\s+again)"
    r"|\bcopy\s+(?:the|this|it)\s*(?:link\s+)?(?:in)?to\s+(?:your\s+)?(?:safari\s+|chrome\s+)?browser\b",
    _I,
)
# The account, SIM, connection or registration is about to be cut off, blocked or lost.
_CUTOFF_THING = (r"(?:account|a/c|sim|card|wallet|connection|power|electricity|supply|service|number|registration|"
                 r"licen[cs]e|vehicle|pan|kyc|mobile|yono|net\s?banking|assets|cryptocurrenc\w*|benefits?)")
_CUTOFF_VERB = (r"(?:block(?:ed)?|suspend(?:ed)?|deactivat\w*|disconnect\w*|terminat\w*|put\s+on\s+hold|on\s+hold|"
                r"frozen|freez\w*|closed|expire\w*|restrict\w*|cancel+ed|no\s+longer\s+(?:be\s+)?(?:taxed|active|valid)|"
                r"cut\s+off)")
CUTOFF_THREAT = re.compile(
    # "will be blocked", "has been suspended", "is no longer taxed": done to you, not "call us to block your card"
    rf"\b{_CUTOFF_THING}\b[^.\n]{{0,50}}?\b(?:will|shall|would|may|has|have|had|is|are|was|were|be|been|get|gets)\b"
    rf"[^.\n]{{0,20}}?\b{_CUTOFF_VERB}"
    rf"|\b(?:will|shall|going\s+to)\s+(?:be\s+)?{_CUTOFF_VERB}\b[^.\n]{{0,30}}?\b(?:your|the)\s+(?:\w+\s+)?"
    rf"{_CUTOFF_THING}\b"
    r"|\blose\s+all\s+(?:of\s+)?your\b|\bno\s+longer\s+(?:be\s+)?able\s+to\s+use\b"
    r"|(?:खाता|सिम|कनेक्शन)[^\n।]{0,30}?(?:बंद|ब्लॉक)",
    _I,
)
# "Visit your nearest branch": a genuine re-KYC reminder offers the branch (RBI's own advice); a phishing message
# needs you on its link or number.
BRANCH_ROUTE = re.compile(r"\b(?:visit|at|to)\s+(?:your|the|any|a)\s+(?:(?:nearest|nearby|home|base|local)\s+)?"
                          r"(?:bank\s+)?branch(?:es)?\b", _I)
# "Your account will not be blocked": the cut-off is denied inside the match itself.
CUTOFF_DENIED = re.compile(r"\b(?:not|never)\b|n't\b", _I)
KYC_TERM = re.compile(r"\b(?:re-?|e-?|v-?)?kyc\b|\bpan\s*(?:card|number|no\b)|\bupdate\w*\s+(?:your\s+)?pan\b"
                      r"|\baadhaa?r\s+(?:link|linking|seeding|update|verification)|\bsim\s+verification\b"
                      r"|केवाईसी|पैन\s*कार्ड", _I)
KYC_ACTION = re.compile(r"\b(?:updat\w*|verif\w*|complete|re-?submit|link|renew|call|contact|click)\b|अपडेट", _I)
# Unsolicited windfalls: prizes, lottery wins, jobs you never applied for, cheap "government scheme" loans.
PRIZE_LURE = re.compile(
    r"\byou(?:'ve|\s+have)?\s+(?:just\s+)?won\b(?!['’]t)|\bwinners?\b|\bwinning\s+amount\b|\blotter(?:y|ies)\b|\blucky\s+draw\b"
    r"|\bjackpot\b|\bsweepstakes?\b|\bcash\s*prize\b|\bprize\s+money\b|इनाम|लॉटरी|विजेता",
    _I,
)
JOB_LURE = re.compile(
    r"\b(?:cv|resume|profile)\s+(?:has|have|is)\s+been\s+(?:selected|shortlisted)\b|\bdaily\s+(?:salary|income|wages?)\b"
    r"|\bearn\s+(?:rs\.?|₹|\$|inr)?\s?\d[\d,]*\s*(?:-\s*\d[\d,]*\s*)?(?:per|a|/)\s*(?:day|hour)\b"
    r"|\bwork(?:ing)?\s+(?:from|on)\s+(?:the\s+)?home\b[^\n]{0,60}?\b(?:salary|earn|income)\b"
    r"|\bpart[\s-]time\s+(?:job|work)\b[^\n]{0,60}?\b(?:salary|earn|income|daily)\b",
    _I,
)
LOAN_LURE = re.compile(
    r"\b(?:pre-?approved|instant|guaranteed)\s+loan\b|\bloan\b[^.\n]{0,40}?\d+(?:\.\d+)?\s?%\s*(?:interest|ब्याज)"
    r"|(?:लोन|ऋण)[^\n]{0,40}?(?:ब्याज|माफ)",
    _I,
)
# Money "waiting for you" that you must do something through the message to receive.
MONEY_WAITING = re.compile(r"\brefund\b|\bcredited\b|\bcashback\b|\bcompensation\b|\bunclaimed\s+(?:money|funds)\b"
                           r"|रिफंड", _I)
MONEY_CLAIMED = re.compile(r"\bapprov\w*|\bentitled\b|\bpending\b|\boverdue\b|\bcredited\b|\beligible\b|\bawaiting\b"
                           r"|\bon\s+hold\b|\bunclaimed\b|\d", _I)
CLAIM_ACTION = re.compile(
    r"\b(?:claim|click|tap|link|verify|update|confirm|proceed|apply|input|enter|fill|submit|call|contact|reply)\b", _I)
# A fee you must pay before a prize, refund, job or parcel is released to you.
FEE_TO_RELEASE = re.compile(
    r"\b(?:registration|registeration|processing|clearance|release|delivery|re-?delivery|verification|activation|"
    r"handling|documentation|courier|shipping|customs)\s+(?:fees?|charg\w*|deposit)"
    r"|\b(?:pay|deposit|send)\b[^.\n]{0,40}?\b(?:fees?|charg\w*)\b[^.\n]{0,40}?"
    r"\b(?:release|receive|claim|collect|deliver\w*)\b"
    r"|(?:पंजीकरण|प्रोसेसिंग)\s*(?:शुल्क|फीस|चार्ज)",
    _I,
)
FEE_CONTEXT_STRONG = re.compile(PRIZE_LURE.pattern + r"|" + JOB_LURE.pattern + r"|\brefund\b|\bwinnings?\b"
                                r"|\bjob\b|\bsalary\b|\bwelcome\s+kit\b", _I)
FEE_CONTEXT_PARCEL = re.compile(r"\bparcel\b|\bpackage\b|\bshipment\b|\bcourier\b|\bconsignment\b|पार्सल", _I)
# "Press 1 to speak to an officer", "press 9 now": a recorded call. "Press 2 for Spanish" is a phone menu.
PRESS_TO_CONNECT = re.compile(
    r"\bpress\s+(?:\d|one|two|nine|zero)\b(?:\s+(?:now|immediately)\b|[^.\n]{0,40}?\bto\s+(?:speak|talk|connect|"
    r"be\s+connected|reach|stop|be\s+removed|avoid|confirm|accept|verify|pay|hear\s+more|know\s+more)\b)",
    _I,
)
CALL_VERB = re.compile(r"\b(?:call|contact|ring|dial|whats\s*app|reach|speak\s+(?:to|with))\b|कॉल|संपर्क", _I)
# "If you did not make this payment, call ...": the fake-invoice call-back.
NOT_YOU = re.compile(r"\bif\s+you\s+(?:did\s+not|didn't|have\s+not|haven't|do\s+not|don't)\s+(?:make|authori[sz]e|"
                     r"recogni[sz]e|place|request|initiate)\b", _I)
ACCOUNT_VERIFY = re.compile(
    r"\b(?:verify|confirm|update|validate|re-?enter|input)\s+(?:\w+\s+){0,3}?(?:identity|details|information|account|"
    r"kyc|pan|bank|card|billing|credentials)\b|\bidentify\s+yourself\b|\bcomplete\s+your\s+identification\b"
    r"|\b(?:details?|information)\s+(?:is|are)\s+incorrect\b",
    _I,
)
# A model "threat" quote that names the police only as the sender ("Delhi Traffic Police: e-Challan No",
# "-Delhi Traffic Police") threatens nothing unless it also names a consequence. Paraphrased threats with no police
# name ("Our team will be at your door with handcuffs") still count.
POLICE_BENIGN = re.compile(r"(?:\b[A-Z][\w-]*\s+){1,3}Police\b"  # a named force as sender
                           r"|(?i:\bpolice\b(?=[^.\n]{0,25}\bverification\b))")  # passport police verification
THREAT_CONSEQUENCE = re.compile(
    THREAT.pattern + r"|\barrest|\bwarrant|\bjail|\bprison|\bcustody|\bdeport|\blegal\s+(?:action|proceedings?|case)"
    r"|\bprosecut|\bcriminal\b|\blawsuit|\bsue\b|\bsummons?\b|\bseiz|\bcase\s+against\b"
    r"|\bpolice\s+(?:action|case|complaint|will)\b",
    _I,
)
# "Failure to respond to this summons may result in ...": a consequence of ignoring a letter, stated as courts and
# agencies state it.
IF_IGNORED = re.compile(r"\b(?:failure\s+to|if\s+you\s+(?:do\s+not|don't|fail\s+to)|unless\s+you)\s+"
                        r"(?:respond|reply|appear|attend|comply|return)\b", _I)
# Telling the reader to report something to the police is advice, not a threat.
REPORT_TO_POLICE = re.compile(r"\b(?:report|contact|call|notify|tell|inform|file)\b[^.\n]{0,50}?"
                              r"\b(?:police|sheriff|law\s+enforcement)\b", _I)
# "From: Companies House <x@example.com>" or "[mailto: x@gmail.com]": who an email says it is from.
FROM_HEADER = re.compile(r"^[ \t]*From\s*:\s*(?P<name>[^<\[\n@]{2,80}?)\s*[<\[]\s*(?:mailto:\s*)?"
                         r"(?P<addr>[^>\s]*?@[^>\]\s]+)\s*[>\]]", _I | re.M)
