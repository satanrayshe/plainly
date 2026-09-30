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
    r"|\b(?:bitcoin|crypto|btc)\s*atm\b|\bwire\s*transfer\b|\bwire\s+(?:the\s+)?(?:money|funds|amount|payment)\b"
    r"|\bwestern\s*union\b|\bmoney\s*gram\b|\b(?:safe|secure|secret)\s+(?:bank\s+)?account\b"
    r"|\brbi\s+(?:verification\s+|safe\s+|escrow\s+)?account\b|बिटकॉइन|क्रिप्टो",
    _I,
)

UPI_CONTEXT = re.compile(r"\bupi\b|\bvpa\b|\bphone\s*pe\b|\bg\s?pay\b|\bgoogle\s*pay\b|\bpaytm\b|\bbhim\b"
                         r"|\bscan\b|\bqr\b|फोनपे|पेटीएम|यूपीआई", _I)
PAYMENT_APP_TO_MOBILE = re.compile(
    r"(?:\bphone\s*pe\b|\bg\s?pay\b|\bgoogle\s*pay\b|\bpaytm\b|\bbhim\b|\bupi\b|फोनपे|पेटीएम|यूपीआई)"
    r"[^.\n।]{0,40}?(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
    r"|(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)[^.\n।]{0,30}?"
    r"(?:\bphone\s*pe\b|\bg\s?pay\b|\bgoogle\s*pay\b|\bpaytm\b|\bbhim\b|\bupi\b|फोनपे|पेटीएम)",
    _I,
)
UPI_PROVIDERS = {
    "okaxis", "okhdfcbank", "okicici", "oksbi", "ybl", "ibl", "axl", "paytm", "ptyes", "ptaxis", "pthdfc", "ptsbi",
    "upi", "apl", "yapl", "rapl", "jio", "fam", "axisbank", "icici", "sbi", "hdfcbank", "kotak", "idfcbank", "axisb",
    "fbl", "freecharge", "airtel", "pingpay", "waicici", "wahdfcbank", "waaxis", "wasbi", "abfspay", "naviaxis",
    "superyes", "yesbank", "barodampay", "unionbank", "pnb", "cnrb", "boi", "indus", "federal", "kbl", "aubank",
    "rbl", "idbi", "ikwik", "mahb", "kvb", "cub", "uco", "psb", "indianbank", "iob", "centralbank", "dcb", "equitas",
}

CREDENTIAL = (
    r"\bOTP\b|\bone[\s-]?time[\s-]?(?:password|pin|passcode|code)\b"
    r"|\b(?:UPI|ATM|M|T|card|debit\s+card|credit\s+card|secret|net\s?banking)[\s-]?PIN\b|\bPIN\b(?!\s*(?:code|:?\s*\d{6}))"
    r"|\bpass\s?words?\b|\bpass\s?code\b|\bCVV\b|\bCVC\b|\bcard\s+verification\b"
    r"|\b(?:full|complete|entire|whole)\s+(?:SSN|social\s+security\s+(?:number|no))\b|\ball\s+9\s+digits\b"
    r"|\b(?:full|complete|entire|whole|12[\s-]digit)\s+aadhaa?r\b"
    r"|\bnet[\s-]?banking\s+(?:login|user\s*(?:name|id)|password|credentials|details)\b"
    r"|\blog\s?in\s+(?:credentials|details)\b|ओटीपी|पिन|पासवर्ड|सीवीवी"
)
REQUEST_VERB = (
    r"\b(?:share|send|provide|tell|give|confirm|enter|reply(?:\s+with)?|forward|read\s+out|read\s+back|verify|update|"
    r"submit|disclose|type|mention|note\s+down|dictate|spell\s+out)\b"
    r"|बताएं|बताइए|बताओ|बताना|भेजें|भेजिए|भेजो|शेयर\s*करें|शेयर\s*कीजिए|साझा\s*करें|दीजिए"
)
CREDENTIAL_REQUEST = re.compile(
    rf"(?P<verb>{REQUEST_VERB})(?:[^.\n।?!]|\.(?=\S)){{0,60}}?(?P<cred>{CREDENTIAL})"
    rf"|(?P<cred2>{CREDENTIAL})(?:[^.\n।?!]|\.(?=\S)){{0,30}}?(?P<verb2>{REQUEST_VERB})",
    _I,
)
# Negation directly before the request verb: "never share", "do not ever share", "न बताएं".
VERB_NEGATION = re.compile(r"(?:\bnever|\bnot|n't|\bno\s+one|\bnobody|न|मत|नहीं|कभी)\s*(?:\w+\s+)?$", _I)

THREAT = re.compile(
    r"\barrest(?:ed|ing)?\b|\bdigital\s+arrest\b|\bwarrants?\b|\bdeport(?:ed|ation)?\b|(?-i:\bFIR\b)"
    r"|\b(?:registered|filed|lodged|booked)\s+(?:a\s+)?(?:criminal\s+)?(?:case|complaint)\s+against\s+you\b"
    r"|\bjail(?:ed)?\b|\bprison\b|\bimprison(?:ment|ed)?\b|\bcustody\b|\bnarcotics\b|\bmoney\s+laundering\b"
    r"|\bdrugs?\s+(?:were|was|have\s+been|has\s+been)\s+(?:found|seized)\b"
    r"|(?-i:\bCBI\b)\s+(?:\w+\s+){0,3}?(?:case|investigation|inquiry|custody|arrest|officer)"
    r"|\bpolice\s+(?:\w+\s+){0,3}?(?:arrest|come|visit|raid|case|complaint|custody|action)"
    r"|\b(?:report|hand(?:ed)?\s+over|forward(?:ed)?|refer(?:red)?)\s+(?:\w+\s+){0,3}?to\s+(?:the\s+)?"
    r"(?:police|cyber\s*cell|court|CBI|narcotics)\b"
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
    r"|सरकार|विभाग|बिजली|मंत्रालय|पुलिस|न्यायालय|निगम",
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
                     r"|\botherwise\b|\belse\b|\bfailing\s+(?:which|this|that)\b|वरना|नहीं\s*तो", _I)
