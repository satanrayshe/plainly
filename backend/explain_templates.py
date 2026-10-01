"""/api/explain without a model: plain-language explanations built from written templates.

Used when AI_MODE=off (the live site on the AWS Free plan). Everything here is fixed text, written by people, in
English, Hindi (हिन्दी) and Spanish (Español), filled with facts from the verified check only:
  - tldr and 3-6 explanation points for the verdict, with one plain line for each rule that flagged,
  - actions: standard steps for the verdict, the deadlines code worked out, and one step for each flagged rule,
  - jargon: terms from a glossary of common official-letter words that appear in the letter,
  - questions_to_ask, and a reply draft (never for a likely scam) in the language of the letter.
Any other language gets the English text and meta.fallback_language = true. The response has the same shape as
the model's (docs/CONTRACT.md, POST /api/explain).
"""
import re
import time
from datetime import date

LANGS = ("en", "hi", "es")
LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "es": "Spanish"}
_LANGUAGE_ALIASES = {
    "en": ("english", "en", "inglés", "ingles", "अंग्रेज़ी", "अंग्रेजी"),
    "hi": ("hindi", "hi", "हिन्दी", "हिंदी", "hindi (हिन्दी)", "हिन्दी (hindi)"),
    "es": ("spanish", "es", "español", "espanol", "castellano", "español (spanish)"),
}
MAX_EXPLANATION = {"simple": 5, "normal": 6}
MAX_ACTIONS = 8
MAX_JARGON = 8
MAX_QUESTIONS = 5


def resolve_language(requested):
    """"en" / "hi" / "es" for a language we have templates for, else None."""
    value = re.sub(r"\s+", " ", str(requested or "").strip().lower())
    for code, aliases in _LANGUAGE_ALIASES.items():
        if value in aliases:
            return code
    return None


# ---------------------------------------------------------------- wording shared by several parts

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
    "hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर",
           "दिसंबर"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
           "noviembre", "diciembre"],
}

PHRASES = {
    "en": {
        "official_phone_site": "the official number for {agency}, {phone} (or {site})",
        "official_phone": "the official number for {agency}, {phone}",
        "official_site": "the official website for {agency}, {site}",
        "official_none": "the organisation on a number you look up yourself, on its own website or an old bill or card",
        "official_short_none": "the official number",
        "site_none": "the official website or app, which you open yourself",
        "report_url_phone": "{name}: {url} (or call {phone})",
        "report_url": "{name}: {url}",
        "report_none": "US: reportfraud.ftc.gov. India: cybercrime.gov.in or call 1930. UK: reportfraud.police.uk "
                       "or call 0300 123 2040.",
        "deadline_step": "Deadline: {date}",
        "deadline_quote": "The letter says: “{what}”.",
        "deadline_plain": "Look for the line with this date in the letter.",
        "computed_letter": " Worked out in code: {days} days after the letter's date.",
        "computed_receipt": " Worked out in code: {days} days after the day you received it (taken as {received}).",
        "amounts": "It mentions {amounts}.",
        "one_deadline": "The deadline in the letter is {date}.",
        "many_deadlines": "The letter has {n} deadlines. The first is {date}.",
        "no_deadline": "We did not find a deadline in the letter.",
        "reply_other_language": "The reply draft below is in {letter_language}, the language of the letter, so the "
                                "office can read it.",
        "letter_languages": {"en": "English", "hi": "Hindi", "es": "Spanish"},
        "sender_unknown": "the sender",
    },
    "hi": {
        "official_phone_site": "{agency} का आधिकारिक नंबर {phone} (या वेबसाइट {site})",
        "official_phone": "{agency} का आधिकारिक नंबर {phone}",
        "official_site": "{agency} की आधिकारिक वेबसाइट {site}",
        "official_none": "संस्था के ऐसे नंबर (जो आप ख़ुद ढूँढें, जैसे उसकी अपनी वेबसाइट या किसी पुराने बिल या कार्ड से)",
        "official_short_none": "आधिकारिक नंबर",
        "site_none": "आधिकारिक वेबसाइट या ऐप, जिसे आप ख़ुद खोलें",
        "report_url_phone": "{name}: {url} (या {phone} पर फ़ोन करें)",
        "report_url": "{name}: {url}",
        "report_none": "भारत: cybercrime.gov.in या 1930 पर फ़ोन करें। अमेरिका: reportfraud.ftc.gov। "
                       "ब्रिटेन: reportfraud.police.uk या 0300 123 2040।",
        "deadline_step": "आख़िरी तारीख़: {date}",
        "deadline_quote": "पत्र में लिखा है: “{what}”।",
        "deadline_plain": "पत्र में इस तारीख़ वाली पंक्ति देखें।",
        "computed_letter": " यह तारीख़ कोड ने गिनी है: पत्र की तारीख़ से {days} दिन बाद।",
        "computed_receipt": " यह तारीख़ कोड ने गिनी है: पत्र मिलने के दिन ({received} माना गया) से {days} दिन बाद।",
        "amounts": "इसमें यह रकम लिखी है: {amounts}।",
        "one_deadline": "पत्र में आख़िरी तारीख़ {date} है।",
        "many_deadlines": "पत्र में {n} आख़िरी तारीख़ें हैं। पहली {date} है।",
        "no_deadline": "हमें पत्र में कोई आख़िरी तारीख़ नहीं मिली।",
        "reply_other_language": "नीचे दिया जवाब का मसौदा {letter_language} में है, क्योंकि पत्र उसी भाषा में है और "
                                "दफ़्तर उसे पढ़ सकेगा।",
        "letter_languages": {"en": "अंग्रेज़ी", "hi": "हिन्दी", "es": "स्पैनिश"},
        "sender_unknown": "भेजने वाले",
    },
    "es": {
        "official_phone_site": "{agency} en su número oficial, {phone} (o en {site})",
        "official_phone": "{agency} en su número oficial, {phone}",
        "official_site": "{agency} en su sitio web oficial, {site}",
        "official_none": "la organización por un número que usted mismo busque, en su sitio web o en una factura o "
                         "tarjeta anterior",
        "official_short_none": "el número oficial",
        "site_none": "el sitio web o la aplicación oficial, abiertos por usted mismo",
        "report_url_phone": "{name}: {url} (o llame al {phone})",
        "report_url": "{name}: {url}",
        "report_none": "EE. UU.: reportfraud.ftc.gov. India: cybercrime.gov.in o llame al 1930. Reino Unido: "
                       "reportfraud.police.uk o llame al 0300 123 2040.",
        "deadline_step": "Fecha límite: {date}",
        "deadline_quote": "La carta dice: “{what}”.",
        "deadline_plain": "Busque en la carta la línea con esta fecha.",
        "computed_letter": " Calculada en código: {days} días después de la fecha de la carta.",
        "computed_receipt": " Calculada en código: {days} días después del día en que la recibió (se tomó el "
                            "{received}).",
        "amounts": "Menciona estas cantidades: {amounts}.",
        "one_deadline": "La fecha límite de la carta es el {date}.",
        "many_deadlines": "La carta tiene {n} fechas límite. La primera es el {date}.",
        "no_deadline": "No encontramos ninguna fecha límite en la carta.",
        "reply_other_language": "El borrador de respuesta de abajo está en {letter_language}, el idioma de la carta, "
                                "para que la oficina pueda leerlo.",
        "letter_languages": {"en": "inglés", "hi": "hindi", "es": "español"},
        "sender_unknown": "el remitente",
    },
}

# ---------------------------------------------------------------- per verdict

VERDICT_TEXT = {
    "likely_scam": {
        "en": {
            "tldr": "This looks like a scam. Do not pay, and do not call, click or reply to anything in it.",
            "sign": " The clearest warning sign: {sign}.",
            "intro": "Plainly checked the letter against fixed rules written in code. Together, the warning signs "
                     "it found add up to a likely scam.",
            "points": [
                "Scammers copy the names of real offices. A familiar name does not make a message real.",
                "If you already paid, or shared a code or password, contact your bank straight away and report it.",
            ],
        },
        "hi": {
            "tldr": "यह धोखाधड़ी (स्कैम) लगता है। कोई पैसा न दें, और इसमें दिए किसी नंबर, लिंक या पते पर कॉल, क्लिक "
                    "या जवाब न करें।",
            "sign": " सबसे साफ़ चेतावनी: {sign}।",
            "intro": "Plainly ने इस पत्र को कोड में लिखे तय नियमों से जाँचा। इसमें मिले चेतावनी के संकेत मिलकर "
                     "बताते हैं कि यह शायद धोखाधड़ी है।",
            "points": [
                "ठग असली दफ़्तरों के नाम की नक़ल करते हैं। जाना-पहचाना नाम होने से संदेश असली नहीं हो जाता।",
                "अगर आप पैसे दे चुके हैं, या कोई कोड या पासवर्ड बता चुके हैं, तो तुरंत अपने बैंक से संपर्क करें और "
                "शिकायत दर्ज करें।",
            ],
        },
        "es": {
            "tldr": "Esto parece una estafa. No pague y no llame, no haga clic ni responda a nada de lo que contiene.",
            "sign": " La señal más clara: {sign}.",
            "intro": "Plainly revisó la carta con reglas fijas escritas en código. Las señales de alerta que "
                     "encontró, juntas, indican que probablemente es una estafa.",
            "points": [
                "Los estafadores copian los nombres de oficinas reales. Un nombre conocido no hace que un mensaje "
                "sea real.",
                "Si ya pagó o compartió un código o una contraseña, llame a su banco de inmediato y denúncielo.",
            ],
        },
    },
    "consistent_with_genuine": {
        "en": {
            "tldr": "This looks like a genuine {agency} letter: its contact details match the official ones and we "
                    "found no warning signs. Still, confirm it on {official_short} before you pay or share anything.",
            "intro": "The contact details in the letter match the official list we keep for {agency}, and the "
                     "wording has none of the warning signs we check for.",
            "points": [
                "That is a good sign, but not proof: a scammer can copy a real letter. Always use the official "
                "number, not only one printed on the letter.",
            ],
        },
        "hi": {
            "tldr": "यह {agency} के असली पत्र जैसा लगता है: इसके संपर्क विवरण आधिकारिक विवरण से मिलते हैं और हमें "
                    "कोई चेतावनी का संकेत नहीं मिला। फिर भी, पैसे देने या कोई जानकारी देने से पहले "
                    "{official_short} पर इसकी पुष्टि करें।",
            "intro": "पत्र में दिए संपर्क विवरण {agency} की उस आधिकारिक सूची से मिलते हैं जो हमारे पास है, और "
                     "इसकी भाषा में वे चेतावनी के संकेत नहीं हैं जिन्हें हम जाँचते हैं।",
            "points": [
                "यह अच्छा संकेत है, पर पक्का सबूत नहीं: ठग असली पत्र की नक़ल भी कर सकते हैं। हमेशा आधिकारिक नंबर "
                "इस्तेमाल करें, सिर्फ़ पत्र पर छपा नंबर नहीं।",
            ],
        },
        "es": {
            "tldr": "Parece una carta auténtica de {agency}: sus datos de contacto coinciden con los oficiales y no "
                    "encontramos señales de alerta. Aun así, antes de pagar o dar datos, confírmela con "
                    "{official_short}.",
            "intro": "Los datos de contacto de la carta coinciden con la lista oficial que tenemos de {agency}, y "
                     "el texto no tiene ninguna de las señales de alerta que revisamos.",
            "points": [
                "Es una buena señal, pero no una prueba: un estafador puede copiar una carta real. Use siempre el "
                "número oficial, no solo el que aparece en la carta.",
            ],
        },
    },
    "cant_tell": {
        "en": {
            "tldr_no_agency": "We can't tell if this is real. We couldn't match the sender to an organisation we "
                              "hold official contacts for, so check it yourself before you do anything.",
            "tldr_flags": "We can't tell if this is real. Some details don't fit a genuine {agency} letter, so check "
                          "with {agency} directly before you do anything.",
            "tldr_plain": "We can't tell if this is real. We couldn't confirm it against the official contacts "
                          "for {agency}, so check with {agency} directly before you do anything.",
            "intro": "“Can't tell” does not mean the letter is fake, and it does not mean it is real. It means you "
                     "should check it yourself before you act.",
            "points": [
                "Use contact details you find yourself, not the ones printed in the letter.",
            ],
        },
        "hi": {
            "tldr_no_agency": "हम नहीं बता सकते कि यह असली है या नहीं। भेजने वाला किसी ऐसी संस्था से नहीं मिला जिसके "
                              "आधिकारिक संपर्क हमारे पास हैं, इसलिए कुछ भी करने से पहले ख़ुद जाँच करें।",
            "tldr_flags": "हम नहीं बता सकते कि यह असली है या नहीं। कुछ बातें {agency} के असली पत्र से मेल नहीं "
                          "खातीं, इसलिए कुछ भी करने से पहले सीधे {agency} से पता करें।",
            "tldr_plain": "हम नहीं बता सकते कि यह असली है या नहीं। हम इसे {agency} के आधिकारिक संपर्कों से पक्का "
                          "नहीं कर पाए, इसलिए कुछ भी करने से पहले सीधे {agency} से पता करें।",
            "intro": "“पता नहीं” का मतलब यह नहीं कि पत्र नक़ली है, और यह भी नहीं कि असली है। इसका मतलब है कि कुछ "
                     "करने से पहले आप ख़ुद जाँच लें।",
            "points": [
                "ऐसे संपर्क विवरण इस्तेमाल करें जो आपने ख़ुद ढूँढे हों, पत्र में छपे विवरण नहीं।",
            ],
        },
        "es": {
            "tldr_no_agency": "No podemos saber si es real. No pudimos relacionar al remitente con ninguna "
                              "organización de la que tengamos contactos oficiales, así que compruébelo usted mismo "
                              "antes de hacer nada.",
            "tldr_flags": "No podemos saber si es real. Algunos detalles no encajan con una carta auténtica de "
                          "{agency}, así que consulte directamente con {agency} antes de hacer nada.",
            "tldr_plain": "No podemos saber si es real. No pudimos confirmarla con los contactos oficiales de "
                          "{agency}, así que consulte directamente con {agency} antes de hacer nada.",
            "intro": "“No se sabe” no significa que la carta sea falsa, ni que sea real. Significa que debe "
                     "comprobarla usted mismo antes de actuar.",
            "points": [
                "Use datos de contacto que usted mismo busque, no los que vienen en la carta.",
            ],
        },
    },
}

# The same three kinds of sender name the tldr needs when no agency matched.
_NO_AGENCY = {"en": "the sender", "hi": "भेजने वाले", "es": "el remitente"}

# ---------------------------------------------------------------- per rule

RULE_TEXT = {
    "payment_gift_card": {
        "en": {"title": "It asks for payment by gift card",
               "means": "Real offices, courts and power companies never take gift cards. Once you share the card "
                        "numbers, the money is gone.",
               "step": "Do not buy or send gift cards",
               "how": "If you already shared gift card numbers, call the card company (the number is on the back of "
                      "the card) and ask them to freeze it."},
        "hi": {"title": "यह गिफ़्ट कार्ड से भुगतान माँगता है",
               "means": "असली सरकारी दफ़्तर, अदालतें या बिजली कंपनियाँ कभी गिफ़्ट कार्ड से पैसे नहीं लेतीं। कार्ड का "
                        "नंबर बताते ही पैसा चला जाता है।",
               "step": "गिफ़्ट कार्ड न ख़रीदें, न भेजें",
               "how": "अगर आप कार्ड का नंबर बता चुके हैं, तो कार्ड के पीछे लिखे नंबर पर कंपनी को फ़ोन करके कार्ड "
                      "रुकवाएँ।"},
        "es": {"title": "Pide el pago con tarjetas de regalo",
               "means": "Ninguna oficina, tribunal ni compañía eléctrica acepta tarjetas de regalo. Si comparte los "
                        "números de la tarjeta, el dinero se pierde.",
               "step": "No compre ni envíe tarjetas de regalo",
               "how": "Si ya compartió los números, llame a la empresa de la tarjeta (el número está al reverso) y "
                      "pida que la bloqueen."},
    },
    "payment_crypto_wire": {
        "en": {"title": "It asks for crypto, a wire transfer or a transfer to a “safe account”",
               "means": "Government offices don't collect money in cryptocurrency, by Western Union or MoneyGram, or "
                        "into a “safe account”. Money sent this way is almost impossible to get back.",
               "step": "Do not send crypto or wire money",
               "how": "If you already sent money, contact your bank or the transfer company at once and ask them to "
                      "stop or reverse it."},
        "hi": {"title": "यह क्रिप्टो, वायर ट्रांसफ़र या किसी “सेफ़ अकाउंट” में पैसे माँगता है",
               "means": "सरकारी दफ़्तर क्रिप्टोकरेंसी, वेस्टर्न यूनियन, मनीग्राम या किसी “सेफ़ अकाउंट” में पैसे नहीं "
                        "लेते। ऐसे भेजा गया पैसा लगभग कभी वापस नहीं मिलता।",
               "step": "क्रिप्टो या वायर ट्रांसफ़र से पैसे न भेजें",
               "how": "अगर पैसे भेज चुके हैं, तो तुरंत अपने बैंक या ट्रांसफ़र कंपनी से बात करें और पैसा रुकवाने को "
                      "कहें।"},
        "es": {"title": "Pide criptomonedas, una transferencia o un envío a una “cuenta segura”",
               "means": "Las oficinas del gobierno no cobran en criptomonedas, por Western Union o MoneyGram, ni en "
                        "una “cuenta segura”. El dinero enviado así casi nunca se recupera.",
               "step": "No envíe criptomonedas ni transferencias",
               "how": "Si ya envió dinero, llame de inmediato a su banco o a la empresa de envíos y pida que lo "
                      "detengan o lo devuelvan."},
    },
    "payment_personal_upi": {
        "en": {"title": "It asks you to pay a personal UPI ID or phone number",
               "means": "A government office or power company takes money through its own official payment page or "
                        "app, not into a person's UPI ID or mobile number.",
               "step": "Do not pay a UPI ID or number from the message",
               "how": "Pay bills only in the official app or website you open yourself. If you already paid, call "
                      "1930 or your bank at once."},
        "hi": {"title": "यह किसी व्यक्ति की UPI आईडी या मोबाइल नंबर पर पैसे माँगता है",
               "means": "सरकारी दफ़्तर या बिजली कंपनी अपने आधिकारिक पेमेंट पेज या ऐप से पैसे लेती है, किसी व्यक्ति "
                        "की UPI आईडी या मोबाइल नंबर पर नहीं।",
               "step": "संदेश में दी गई UPI आईडी या नंबर पर पैसे न भेजें",
               "how": "बिल सिर्फ़ उसी आधिकारिक ऐप या वेबसाइट से भरें जिसे आप ख़ुद खोलें। अगर पैसे भेज चुके हैं, तो "
                      "तुरंत 1930 या अपने बैंक को फ़ोन करें।"},
        "es": {"title": "Pide pagar a un UPI o a un número de teléfono personal",
               "means": "Una oficina del gobierno o una compañía eléctrica cobra en su propia página o aplicación "
                        "oficial, no en la cuenta UPI ni en el móvil de una persona.",
               "step": "No pague a un UPI ni a un número del mensaje",
               "how": "Pague sus facturas solo en la aplicación o el sitio oficial que usted mismo abra. Si ya pagó, "
                      "llame de inmediato a su banco (en la India, también al 1930)."},
    },
    "credential_request": {
        "en": {"title": "It asks for an OTP, PIN, password or full ID number",
               "means": "No real office or bank asks you to share an OTP, PIN, password or your full SSN or Aadhaar "
                        "number. With these, someone can empty your account.",
               "step": "Never share codes, PINs or passwords",
               "how": "If you already shared one, call your bank on the number on your card, block the card or "
                      "account, and change your passwords."},
        "hi": {"title": "यह OTP, PIN, पासवर्ड या पूरा पहचान नंबर माँगता है",
               "means": "कोई असली दफ़्तर या बैंक आपसे OTP, PIN, पासवर्ड, या पूरा आधार या SSN नंबर नहीं माँगता। "
                        "इनसे कोई भी आपका खाता ख़ाली कर सकता है।",
               "step": "कोई कोड, PIN या पासवर्ड किसी को न बताएँ",
               "how": "अगर बता चुके हैं, तो कार्ड पर लिखे नंबर से अपने बैंक को फ़ोन करें, कार्ड या खाता बंद "
                      "करवाएँ और पासवर्ड बदलें।"},
        "es": {"title": "Pide un código OTP, un PIN, una contraseña o su número de identidad completo",
               "means": "Ninguna oficina ni banco de verdad le pide un código de un solo uso, un PIN, una contraseña "
                        "o su número de Seguro Social o Aadhaar completo. Con eso pueden vaciar su cuenta.",
               "step": "Nunca comparta códigos, PIN ni contraseñas",
               "how": "Si ya compartió alguno, llame a su banco al número que figura en su tarjeta, bloquee la "
                      "tarjeta o la cuenta y cambie sus contraseñas."},
    },
    "threat_arrest": {
        "en": {"title": "It threatens arrest, police action or deportation",
               "means": "Real offices write to you and give you time to reply. Threatening arrest or the police if "
                        "you don't pay right now is a way to scare you into acting fast.",
               "step": "Don't let the threat rush you",
               "how": "No real officer can arrest you over a message or a phone call. Hang up and check with the "
                      "office yourself."},
        "hi": {"title": "यह गिरफ़्तारी, पुलिस या देश से निकालने की धमकी देता है",
               "means": "असली दफ़्तर चिट्ठी भेजकर जवाब देने का समय देते हैं। तुरंत पैसे न देने पर गिरफ़्तारी या "
                        "पुलिस की धमकी आपको डराकर जल्दबाज़ी करवाने का तरीक़ा है।",
               "step": "धमकी से घबराकर जल्दबाज़ी न करें",
               "how": "कोई असली अफ़सर संदेश या फ़ोन कॉल पर आपको गिरफ़्तार नहीं कर सकता। फ़ोन काटें और दफ़्तर से "
                      "ख़ुद पता करें।"},
        "es": {"title": "Amenaza con arresto, policía o deportación",
               "means": "Las oficinas de verdad le escriben y le dan tiempo para responder. Amenazar con arresto o "
                        "con la policía si no paga ya es una forma de asustarle para que actúe rápido.",
               "step": "No deje que la amenaza le apure",
               "how": "Ningún agente de verdad puede arrestarle por un mensaje o una llamada. Cuelgue y consulte "
                      "usted mismo con la oficina."},
    },
    "video_call_demand": {
        "en": {"title": "It demands a video call or that you stay on the line",
               "means": "Police and government offices don't question or “arrest” anyone over a video call. A "
                        "so-called “digital arrest” is always a scam.",
               "step": "End the call",
               "how": "You can hang up at any time. Talk to family or someone you trust, and report the call."},
        "hi": {"title": "यह वीडियो कॉल पर आने या कॉल पर बने रहने को कहता है",
               "means": "पुलिस या सरकारी दफ़्तर वीडियो कॉल पर न पूछताछ करते हैं, न किसी को “गिरफ़्तार” करते हैं। "
                        "“डिजिटल अरेस्ट” हमेशा धोखा होता है।",
               "step": "कॉल काट दें",
               "how": "आप कभी भी फ़ोन काट सकते हैं। परिवार या किसी भरोसेमंद व्यक्ति से बात करें और कॉल की शिकायत "
                      "करें।"},
        "es": {"title": "Exige una videollamada o que no cuelgue",
               "means": "La policía y las oficinas del gobierno no interrogan ni “arrestan” a nadie por "
                        "videollamada. Un supuesto “arresto digital” siempre es una estafa.",
               "step": "Termine la llamada",
               "how": "Puede colgar en cualquier momento. Hable con su familia o con alguien de confianza y "
                      "denuncie la llamada."},
    },
    "ai_instruction": {
        "en": {"title": "It contains hidden text aimed at AI tools",
               "means": "A genuine letter has no reason to talk to AI tools. This text tries to fool scam checkers, "
                        "so we treat it as a strong warning sign and do not repeat it.",
               "step": "Treat the whole letter as suspicious",
               "how": "Don't act on anything in it. Contact the organisation it names through a number or website "
                      "you find yourself."},
        "hi": {"title": "इसमें AI टूल के लिए छिपा हुआ संदेश है",
               "means": "असली पत्र को AI टूल से बात करने की कोई ज़रूरत नहीं होती। यह हिस्सा स्कैम पकड़ने वाले टूल को "
                        "धोखा देने की कोशिश है, इसलिए हम इसे बड़ी चेतावनी मानते हैं और इसे दोहराते नहीं।",
               "step": "पूरे पत्र पर शक करें",
               "how": "इसकी किसी बात पर अमल न करें। जिस संस्था का नाम लिखा है, उससे ख़ुद ढूँढे गए नंबर या वेबसाइट "
                      "से संपर्क करें।"},
        "es": {"title": "Contiene texto oculto dirigido a herramientas de IA",
               "means": "Una carta auténtica no tiene por qué hablarles a herramientas de IA. Ese texto intenta "
                        "engañar a los verificadores de estafas, así que lo tratamos como una señal fuerte y no lo "
                        "repetimos.",
               "step": "Desconfíe de toda la carta",
               "how": "No haga nada de lo que pide. Contacte a la organización que nombra por un número o sitio web "
                      "que usted mismo busque."},
    },
    "lookalike_domain": {
        "en": {"title": "It uses a web or email address that imitates an official one",
               "means": "Scammers register addresses that look like the real one at a glance, with an extra word or "
                        "a changed letter.",
               "step": "Don't open the address in the letter",
               "how": "Type the organisation's real address yourself, or search for it, instead of using the one "
                      "printed here."},
        "hi": {"title": "इसमें किसी आधिकारिक वेबसाइट या ईमेल की नक़ल वाला पता है",
               "means": "ठग ऐसे पते बनाते हैं जो पहली नज़र में असली जैसे दिखें, बस एक शब्द ज़्यादा या एक अक्षर "
                        "बदला हुआ।",
               "step": "पत्र में दिया पता न खोलें",
               "how": "संस्था का असली पता ख़ुद टाइप करें या खोजें, यहाँ छपा पता इस्तेमाल न करें।"},
        "es": {"title": "Usa una dirección web o de correo que imita a una oficial",
               "means": "Los estafadores registran direcciones que a simple vista parecen la verdadera, con una "
                        "palabra de más o una letra cambiada.",
               "step": "No abra la dirección de la carta",
               "how": "Escriba usted mismo la dirección real de la organización, o búsquela, en lugar de usar la "
                      "que aparece aquí."},
    },
    "urgency_short": {
        "en": {"title": "It gives you less than 3 days to act",
               "means": "Very short deadlines are meant to rush you. Real notices usually give you weeks.",
               "step": "Take your time to check",
               "how": "A few hours spent checking will not make things worse with a real office."},
        "hi": {"title": "यह कार्रवाई के लिए 3 दिन से कम समय देता है",
               "means": "बहुत कम समय इसलिए दिया जाता है ताकि आप घबराकर जल्दी करें। असली नोटिस आमतौर पर कई हफ़्ते "
                        "देते हैं।",
               "step": "जाँचने के लिए समय लें",
               "how": "कुछ घंटे जाँच में लगाने से किसी असली दफ़्तर के साथ आपका मामला नहीं बिगड़ेगा।"},
        "es": {"title": "Le da menos de 3 días para actuar",
               "means": "Los plazos muy cortos buscan apurarle. Los avisos reales suelen darle semanas.",
               "step": "Tómese su tiempo para comprobarlo",
               "how": "Dedicar unas horas a comprobarlo no empeorará nada con una oficina de verdad."},
    },
    "freemail_official": {
        "en": {"title": "It gives a free email address as an official contact",
               "means": "Government offices and companies use their own email addresses, not Gmail, Yahoo or "
                        "Outlook.",
               "step": "Don't write to that email address",
               "how": "Use the contact details on the organisation's own website."},
        "hi": {"title": "यह आधिकारिक संपर्क के रूप में मुफ़्त ईमेल पता देता है",
               "means": "सरकारी दफ़्तर और कंपनियाँ अपने ख़ुद के ईमेल पते इस्तेमाल करती हैं, Gmail, Yahoo या "
                        "Outlook नहीं।",
               "step": "उस ईमेल पते पर न लिखें",
               "how": "संस्था की अपनी वेबसाइट पर दिए संपर्क विवरण इस्तेमाल करें।"},
        "es": {"title": "Da un correo gratuito como contacto oficial",
               "means": "Las oficinas del gobierno y las empresas usan sus propias direcciones de correo, no Gmail, "
                        "Yahoo ni Outlook.",
               "step": "No escriba a ese correo",
               "how": "Use los datos de contacto del sitio web propio de la organización."},
    },
    "secrecy": {
        "en": {"title": "It tells you to keep it secret",
               "means": "Scammers tell you not to talk to family or your bank, because those people would stop you.",
               "step": "Tell someone you trust",
               "how": "Show the letter to a family member, a friend or your bank before you do anything."},
        "hi": {"title": "यह इसे किसी को न बताने को कहता है",
               "means": "ठग कहते हैं कि परिवार या बैंक को न बताएँ, क्योंकि वही लोग आपको रोक लेंगे।",
               "step": "किसी भरोसेमंद व्यक्ति को बताएँ",
               "how": "कुछ भी करने से पहले पत्र परिवार के किसी सदस्य, दोस्त या अपने बैंक को दिखाएँ।"},
        "es": {"title": "Le pide que lo mantenga en secreto",
               "means": "Los estafadores le piden que no hable con su familia ni con su banco, porque ellos le "
                        "detendrían.",
               "step": "Cuénteselo a alguien de confianza",
               "how": "Enseñe la carta a un familiar, a un amigo o a su banco antes de hacer nada."},
    },
    "link_bait": {
        "en": {"title": "It asks you to click a link to get money, pay, or “verify” your details",
               "means": "Phishing messages lead you to a fake page with a story: a refund, a bill, or an account "
                        "that will be blocked.",
               "step": "Don't click the link",
               "how": "Go to the organisation's website or app yourself, by typing the address you already know."},
        "hi": {"title": "यह पैसे पाने, भुगतान करने या जानकारी “वेरिफ़ाई” करने के लिए लिंक पर क्लिक करने को कहता है",
               "means": "फ़िशिंग संदेश कोई कहानी बनाकर (रिफ़ंड, बिल, या खाता बंद होने की बात) आपको नक़ली पेज पर ले "
                        "जाते हैं।",
               "step": "लिंक पर क्लिक न करें",
               "how": "संस्था की वेबसाइट या ऐप ख़ुद खोलें, वह पता टाइप करके जो आप पहले से जानते हैं।"},
        "es": {"title": "Le pide hacer clic en un enlace para cobrar, pagar o “verificar” sus datos",
               "means": "Los mensajes de phishing le llevan a una página falsa con una historia: un reembolso, una "
                        "factura o una cuenta que van a bloquear.",
               "step": "No haga clic en el enlace",
               "how": "Entre usted mismo en el sitio web o la aplicación de la organización, escribiendo la "
                      "dirección que ya conoce."},
    },
    "shortened_or_raw_link": {
        "en": {"title": "It uses a short link or a throwaway web address",
               "means": "Short links (like bit.ly), bare number addresses and free website hosts hide who really "
                        "runs the page. Official bodies link to their own website.",
               "step": "Don't open short or strange links",
               "how": "If you want to check, search for the organisation's official website instead."},
        "hi": {"title": "यह छोटा (शॉर्ट) लिंक या कोई अस्थायी वेब पता इस्तेमाल करता है",
               "means": "शॉर्ट लिंक (जैसे bit.ly), सिर्फ़ अंकों वाले पते और मुफ़्त वेबसाइटें यह छिपाती हैं कि पेज "
                        "असल में कौन चला रहा है। सरकारी संस्थाएँ अपनी ख़ुद की वेबसाइट का लिंक देती हैं।",
               "step": "छोटे या अजीब लिंक न खोलें",
               "how": "जाँचना हो तो संस्था की आधिकारिक वेबसाइट ख़ुद खोजें।"},
        "es": {"title": "Usa un enlace acortado o una dirección web desechable",
               "means": "Los enlaces cortos (como bit.ly), las direcciones hechas solo de números y los "
                        "alojamientos web gratuitos ocultan quién está detrás de la página. Los organismos "
                        "oficiales enlazan a su propio sitio web.",
               "step": "No abra enlaces cortos o extraños",
               "how": "Si quiere comprobarlo, busque usted mismo el sitio web oficial de la organización."},
    },
    "kyc_update_threat": {
        "en": {"title": "It says your account or SIM will be blocked unless you update KYC or PAN",
               "means": "Banks and phone companies don't block you through a text with a link or a number to call. "
                        "KYC is updated at the branch, in the official app or on the official website.",
               "step": "Don't update KYC through this message",
               "how": "If you are unsure, visit your branch or open the official app yourself and check there."},
        "hi": {"title": "यह कहता है कि KYC या PAN अपडेट न करने पर खाता या SIM बंद हो जाएगा",
               "means": "बैंक और मोबाइल कंपनियाँ किसी लिंक या नंबर वाले मैसेज से आपका खाता बंद नहीं करतीं। KYC "
                        "ब्रांच में, आधिकारिक ऐप में या आधिकारिक वेबसाइट पर ही अपडेट होता है।",
               "step": "इस संदेश से KYC अपडेट न करें",
               "how": "शक हो तो अपनी ब्रांच जाएँ, या आधिकारिक ऐप ख़ुद खोलकर वहीं देखें।"},
        "es": {"title": "Dice que bloquearán su cuenta o su SIM si no actualiza sus datos KYC o PAN",
               "means": "Los bancos y las compañías telefónicas no le bloquean por un mensaje con un enlace o un "
                        "número al que llamar. Los datos KYC se actualizan en la sucursal, en la aplicación oficial "
                        "o en el sitio web oficial.",
               "step": "No actualice sus datos desde este mensaje",
               "how": "Si tiene dudas, vaya a su sucursal o abra usted mismo la aplicación oficial y compruébelo "
                      "allí."},
    },
    "prize_or_refund_bait": {
        "en": {"title": "It offers a prize, refund, loan or job out of the blue",
               "means": "Money or a job you didn't ask for is the bait. Real refunds arrive without you having to "
                        "click, call or chat with anyone.",
               "step": "Don't reply to claim it",
               "how": "If you are owed a refund, you can see it by logging in to the official website yourself."},
        "hi": {"title": "यह अचानक इनाम, रिफ़ंड, लोन या नौकरी की पेशकश करता है",
               "means": "बिना माँगे पैसा या नौकरी चारा है। असली रिफ़ंड बिना किसी लिंक, कॉल या चैट के अपने आप आता "
                        "है।",
               "step": "इसे पाने के लिए जवाब न दें",
               "how": "अगर आपका कोई रिफ़ंड बनता है, तो आधिकारिक वेबसाइट पर ख़ुद लॉग इन करके देख सकते हैं।"},
        "es": {"title": "Ofrece un premio, un reembolso, un préstamo o un trabajo sin haberlo pedido",
               "means": "El dinero o el trabajo que usted no pidió es el cebo. Los reembolsos reales llegan sin que "
                        "tenga que hacer clic, llamar ni chatear con nadie.",
               "step": "No responda para reclamarlo",
               "how": "Si le deben un reembolso, puede verlo entrando usted mismo en el sitio web oficial."},
    },
    "unexpected_fee_to_release": {
        "en": {"title": "It asks for a fee before you get a prize, refund, job or parcel",
               "means": "Real prizes are free, and honest employers never ask you to pay for a job. A fee to "
                        "release money or goods is how these scams take your money.",
               "step": "Don't pay the fee",
               "how": "For a parcel, check the tracking number on the courier's or post office's own website."},
        "hi": {"title": "यह इनाम, रिफ़ंड, नौकरी या पार्सल से पहले फ़ीस माँगता है",
               "means": "असली इनाम मुफ़्त होते हैं, और ईमानदार नियोक्ता नौकरी के लिए पैसे नहीं माँगते। पैसा या "
                        "सामान “छुड़ाने” की फ़ीस ही इस ठगी का तरीक़ा है।",
               "step": "फ़ीस न भरें",
               "how": "पार्सल हो तो उसका ट्रैकिंग नंबर कूरियर या डाकघर की अपनी वेबसाइट पर जाँचें।"},
        "es": {"title": "Pide pagar una tarifa antes de recibir un premio, un reembolso, un trabajo o un paquete",
               "means": "Los premios de verdad son gratis, y ningún empleador honrado cobra por un trabajo. Una "
                        "tarifa para “liberar” dinero o un paquete es la forma en que estas estafas se quedan con su "
                        "dinero.",
               "step": "No pague la tarifa",
               "how": "Si es un paquete, compruebe el número de seguimiento en el sitio web de la empresa de "
                      "mensajería o de correos."},
    },
    "press_to_connect": {
        "en": {"title": "It tells you to press a number to speak to someone",
               "means": "Recorded calls that say “press 1 to speak to an officer” are robocalls. Offices don't reach "
                        "you this way.",
               "step": "Hang up and don't press anything",
               "how": "Call the official number yourself if you want to check."},
        "hi": {"title": "यह किसी से बात करने के लिए कोई बटन दबाने को कहता है",
               "means": "“अफ़सर से बात करने के लिए 1 दबाएँ” जैसी रिकॉर्ड की हुई कॉल रोबोकॉल होती हैं। दफ़्तर आपसे इस "
                        "तरह संपर्क नहीं करते।",
               "step": "फ़ोन काटें और कोई बटन न दबाएँ",
               "how": "जाँचना हो तो आधिकारिक नंबर पर ख़ुद फ़ोन करें।"},
        "es": {"title": "Le pide pulsar un número para hablar con alguien",
               "means": "Las llamadas grabadas que dicen “pulse 1 para hablar con un agente” son llamadas "
                        "automáticas. Las oficinas no se comunican así.",
               "step": "Cuelgue y no pulse nada",
               "how": "Si quiere comprobarlo, llame usted mismo al número oficial."},
    },
    "callback_unofficial": {
        "en": {"title": "It asks you to call or WhatsApp a number that isn't an official line",
               "means": "Fake bills and disconnection messages give a number that goes straight to the scammer. "
                        "Offices and power companies don't use personal mobile numbers.",
               "step": "Don't call or message that number",
               "how": "Use the number on your last real bill, on your card or on the official website instead."},
        "hi": {"title": "यह ऐसे नंबर पर कॉल या WhatsApp करने को कहता है जो आधिकारिक लाइन नहीं है",
               "means": "नक़ली बिल और बिजली कटने के संदेशों में दिया नंबर सीधे ठग के पास जाता है। दफ़्तर और बिजली "
                        "कंपनियाँ निजी मोबाइल नंबर इस्तेमाल नहीं करतीं।",
               "step": "उस नंबर पर कॉल या मैसेज न करें",
               "how": "अपने पिछले असली बिल, कार्ड या आधिकारिक वेबसाइट पर दिया नंबर इस्तेमाल करें।"},
        "es": {"title": "Le pide llamar o escribir por WhatsApp a un número que no es oficial",
               "means": "Las facturas falsas y los avisos de corte dan un número que va directo al estafador. Las "
                        "oficinas y las compañías eléctricas no usan móviles personales.",
               "step": "No llame ni escriba a ese número",
               "how": "Use el número de su última factura real, de su tarjeta o del sitio web oficial."},
    },
    "impersonation_mismatch": {
        "en": {"title": "It claims to be an official body, but its contact details aren't that body's",
               "means": "The letter uses an official name, but the addresses or numbers in it belong to someone "
                        "else.",
               "step": "Don't trust the contacts in the letter",
               "how": "Contact the organisation it names through details you find yourself."},
        "hi": {"title": "यह किसी सरकारी संस्था का नाम लेता है, पर इसके संपर्क विवरण उस संस्था के नहीं हैं",
               "means": "पत्र में आधिकारिक नाम है, पर इसमें दिए पते या नंबर किसी और के हैं।",
               "step": "पत्र में दिए संपर्कों पर भरोसा न करें",
               "how": "जिस संस्था का नाम लिखा है, उससे ख़ुद ढूँढे गए विवरण से संपर्क करें।"},
        "es": {"title": "Dice ser un organismo oficial, pero sus datos de contacto no son de ese organismo",
               "means": "La carta usa un nombre oficial, pero las direcciones o los números que da son de otra "
                        "persona.",
               "step": "No confíe en los contactos de la carta",
               "how": "Contacte a la organización que nombra con datos que usted mismo busque."},
    },
    "unknown_contact": {
        "en": {"title": "Some contact details are not on the official list",
               "means": "We keep official contacts for a short list of offices. A contact we don't know is not proof "
                        "of a scam, but it is worth checking.",
               "step": "Check the unknown contact",
               "how": "Before you call or write, compare it with the organisation's official website."},
        "hi": {"title": "कुछ संपर्क विवरण आधिकारिक सूची में नहीं हैं",
               "means": "हमारे पास कुछ ही दफ़्तरों के आधिकारिक संपर्क हैं। कोई अनजान संपर्क अपने आप में धोखे का सबूत "
                        "नहीं है, पर उसे जाँच लेना अच्छा है।",
               "step": "अनजान संपर्क की जाँच करें",
               "how": "कॉल करने या लिखने से पहले उसे संस्था की आधिकारिक वेबसाइट से मिलाएँ।"},
        "es": {"title": "Algunos datos de contacto no están en la lista oficial",
               "means": "Solo tenemos contactos oficiales de una lista corta de oficinas. Un contacto desconocido no "
                        "prueba que sea una estafa, pero conviene comprobarlo.",
               "step": "Compruebe el contacto desconocido",
               "how": "Antes de llamar o escribir, compárelo con el sitio web oficial de la organización."},
    },
    "injection_detected_model": {
        "en": {"title": "Part of the letter is aimed at AI tools",
               "means": "Part of the letter speaks to AI tools. We don't repeat it. A genuine letter has no reason to "
                        "do this.",
               "step": "Be careful with this letter",
               "how": "Check it with the organisation through a number or website you find yourself."},
        "hi": {"title": "पत्र का एक हिस्सा AI टूल के लिए लिखा गया है",
               "means": "पत्र का एक हिस्सा AI टूल से बात करता है। हम उसे दोहराते नहीं। असली पत्र में ऐसा करने की कोई "
                        "वजह नहीं होती।",
               "step": "इस पत्र से सावधान रहें",
               "how": "संस्था से ख़ुद ढूँढे गए नंबर या वेबसाइट के ज़रिए इसकी जाँच करें।"},
        "es": {"title": "Una parte de la carta va dirigida a herramientas de IA",
               "means": "Una parte de la carta les habla a herramientas de IA. No la repetimos. Una carta auténtica "
                        "no tiene motivo para hacerlo.",
               "step": "Tenga cuidado con esta carta",
               "how": "Compruébela con la organización por un número o sitio web que usted mismo busque."},
    },
}

# ---------------------------------------------------------------- standard actions per verdict

ACTIONS = {
    "likely_scam": {
        "en": [
            ("Do not pay anything", "Don't send money, gift cards, crypto or codes, even if the letter says it's "
                                    "urgent."),
            ("Don't call the number in the message", "Don't call, click, scan or reply to anything printed in it. "
                                                     "Those contacts go to the sender."),
            ("Contact {agency_or_office} yourself", "If you are worried it might be real, contact {official} and ask."),
            ("Report it", "{report}"),
        ],
        "hi": [
            ("कोई भुगतान न करें", "पैसे, गिफ़्ट कार्ड, क्रिप्टो या कोई कोड न भेजें, चाहे पत्र में कितनी भी जल्दी "
                                  "बताई गई हो।"),
            ("संदेश में दिए नंबर पर कॉल न करें", "इसमें छपे किसी नंबर, लिंक या QR कोड पर कॉल, क्लिक, स्कैन या "
                                                "जवाब न करें। वे सीधे भेजने वाले तक जाते हैं।"),
            ("{agency_or_office} से ख़ुद संपर्क करें", "अगर आपको लगता है कि यह असली हो सकता है, तो {official} पर "
                                                       "संपर्क करके पूछें।"),
            ("शिकायत करें", "{report}"),
        ],
        "es": [
            ("No pague nada", "No envíe dinero, tarjetas de regalo, criptomonedas ni códigos, aunque la carta diga "
                              "que es urgente."),
            ("No llame al número del mensaje", "No llame, no haga clic, no escanee ni responda a nada de lo que "
                                               "trae. Esos contactos van directos a quien lo envió."),
            ("Contacte usted mismo a {agency_or_office}", "Si le preocupa que pueda ser real, contacte a {official} "
                                                          "y pregunte."),
            ("Denúncielo", "{report}"),
        ],
    },
    "consistent_with_genuine": {
        "en": [
            ("Confirm with {agency_or_office} first", "Contact {official} and ask them to confirm the notice. Don't "
                                                      "rely only on a number printed in the letter."),
            ("Pay only through the official website", "If you need to pay, do it on {site}, never through a link in "
                                                      "a message."),
            ("Add the deadline to your calendar", "Use the “Add to calendar” button next to the deadline so you "
                                                  "don't miss it."),
            ("Ask for help if you can't pay on time", "Offices often allow a payment plan or more time if you ask "
                                                      "before the deadline. The reply draft below can help."),
        ],
        "hi": [
            ("पहले {agency_or_office} से पुष्टि करें", "{official} पर संपर्क करें और नोटिस की पुष्टि करने को कहें। "
                                                       "सिर्फ़ पत्र में छपे नंबर पर भरोसा न करें।"),
            ("भुगतान सिर्फ़ आधिकारिक वेबसाइट से करें", "अगर भुगतान करना है, तो {site} पर करें, किसी संदेश के लिंक "
                                                         "से कभी नहीं।"),
            ("आख़िरी तारीख़ कैलेंडर में जोड़ें", "आख़िरी तारीख़ के पास दिए “कैलेंडर में जोड़ें” बटन का इस्तेमाल "
                                                 "करें, ताकि तारीख़ छूटे नहीं।"),
            ("समय पर भुगतान न कर पाएँ तो मदद माँगें", "आख़िरी तारीख़ से पहले पूछने पर दफ़्तर अक्सर किस्तों में "
                                                       "भुगतान या ज़्यादा समय दे देते हैं। नीचे दिया जवाब का मसौदा "
                                                       "इसमें मदद करेगा।"),
        ],
        "es": [
            ("Confírmelo primero con {agency_or_office}", "Contacte a {official} y pida que le confirmen el aviso. "
                                                          "No se fíe solo de un número impreso en la carta."),
            ("Pague solo en el sitio web oficial", "Si tiene que pagar, hágalo en {site}, nunca desde un enlace de "
                                                   "un mensaje."),
            ("Anote la fecha límite en su calendario", "Use el botón “Añadir al calendario” junto a la fecha límite "
                                                       "para no olvidarla."),
            ("Pida ayuda si no puede pagar a tiempo", "Las oficinas suelen aceptar un plan de pagos o darle más "
                                                      "tiempo si lo pide antes de la fecha límite. El borrador de "
                                                      "respuesta de abajo puede ayudarle."),
        ],
    },
    "cant_tell": {
        "en": [
            ("Don't act on the letter yet", "Don't pay, call or click anything in it until you have checked it."),
            ("Find the official contact yourself", "Contact {official} and ask whether they sent it."),
            ("Ask someone you trust", "Show it to a family member, a friend or your bank. A second pair of eyes "
                                      "helps."),
            ("Compare the details", "Check the name, reference number and amount against earlier letters or your "
                                    "account online."),
        ],
        "hi": [
            ("अभी पत्र के हिसाब से कुछ न करें", "जाँच पूरी होने तक इसमें दिए किसी नंबर या लिंक पर भुगतान, कॉल या "
                                                "क्लिक न करें।"),
            ("आधिकारिक संपर्क ख़ुद ढूँढें", "{official} पर संपर्क करें और पूछें कि क्या यह उन्होंने भेजा है।"),
            ("किसी भरोसेमंद व्यक्ति से पूछें", "इसे परिवार के किसी सदस्य, दोस्त या अपने बैंक को दिखाएँ। दूसरी नज़र "
                                              "से मदद मिलती है।"),
            ("विवरण मिलाएँ", "नाम, रेफ़रेंस नंबर और रकम को पुराने पत्रों या अपने ऑनलाइन खाते से मिलाएँ।"),
        ],
        "es": [
            ("No actúe todavía", "No pague, no llame ni haga clic en nada de la carta hasta haberla comprobado."),
            ("Busque usted mismo el contacto oficial", "Contacte a {official} y pregunte si la enviaron ellos."),
            ("Consulte a alguien de confianza", "Enséñela a un familiar, a un amigo o a su banco. Otra mirada "
                                                "ayuda."),
            ("Compare los datos", "Compare el nombre, el número de referencia y la cantidad con cartas anteriores o "
                                  "con su cuenta en línea."),
        ],
    },
}
_OFFICE = {"en": "the organisation", "hi": "संस्था", "es": "la organización"}

# ---------------------------------------------------------------- questions to ask the real office

QUESTIONS = {
    "likely_scam": {
        "en": ["Did you send me this message or letter?", "Is anything pending on my account?",
               "If I owe anything, what is the right way to pay you?",
               "I may have shared details or paid already. What should I do now?"],
        "hi": ["क्या आपने मुझे यह संदेश या पत्र भेजा है?", "क्या मेरे खाते में कुछ बकाया है?",
               "अगर मुझे कुछ देना है, तो भुगतान का सही तरीक़ा क्या है?",
               "हो सकता है मैंने जानकारी दे दी हो या भुगतान कर दिया हो। अब मुझे क्या करना चाहिए?"],
        "es": ["¿Me enviaron ustedes este mensaje o esta carta?", "¿Tengo algo pendiente en mi cuenta?",
               "Si debo algo, ¿cuál es la forma correcta de pagarles?",
               "Puede que ya haya dado datos o pagado. ¿Qué debo hacer ahora?"],
    },
    "consistent_with_genuine": {
        "en": ["Can you confirm this notice was sent to me?", "{amount_question}",
               "Can I pay in instalments, or get more time?", "{deadline_question}"],
        "hi": ["क्या आप पुष्टि कर सकते हैं कि यह नोटिस मुझे ही भेजा गया है?", "{amount_question}",
               "क्या मैं किस्तों में भुगतान कर सकता/सकती हूँ, या मुझे और समय मिल सकता है?", "{deadline_question}"],
        "es": ["¿Pueden confirmarme que este aviso es para mí?", "{amount_question}",
               "¿Puedo pagar a plazos o tener más tiempo?", "{deadline_question}"],
    },
    "cant_tell": {
        "en": ["Did you send this letter to me?", "Is anything pending on my account?",
               "Which number or website should I use to reply?", "What happens if I don't reply?"],
        "hi": ["क्या आपने यह पत्र मुझे भेजा है?", "क्या मेरे खाते में कुछ बकाया है?",
               "जवाब देने के लिए मुझे कौन-सा नंबर या वेबसाइट इस्तेमाल करनी चाहिए?",
               "अगर मैं जवाब न दूँ तो क्या होगा?"],
        "es": ["¿Me enviaron ustedes esta carta?", "¿Tengo algo pendiente en mi cuenta?",
               "¿Qué número o sitio web debo usar para responder?", "¿Qué pasa si no respondo?"],
    },
}
AMOUNT_QUESTION = {
    "en": ("Is the amount of {amount} correct, and how was it worked out?",
           "How much do I owe, and how was it worked out?"),
    "hi": ("क्या {amount} की रकम सही है, और यह कैसे निकाली गई?", "मुझे कितनी रकम देनी है, और यह कैसे निकाली गई?"),
    "es": ("¿Es correcta la cantidad de {amount} y cómo se calculó?", "¿Cuánto debo y cómo se calculó?"),
}
DEADLINE_QUESTION = {
    "en": ("What happens if I miss the {date} deadline?", "Is there a deadline I need to meet?"),
    "hi": ("अगर {date} की आख़िरी तारीख़ छूट जाए तो क्या होगा?", "क्या कोई आख़िरी तारीख़ है जिसका मुझे ध्यान रखना है?"),
    "es": ("¿Qué pasa si no cumplo la fecha límite del {date}?", "¿Hay alguna fecha límite que deba cumplir?"),
}

# ---------------------------------------------------------------- reply draft (never for a likely scam)

REPLY = {
    "en": {
        "to": "To: {recipient}",
        "subject_dated": "Subject: Your notice dated {date}",
        "subject": "Subject: Your recent notice",
        "greeting": "Dear Sir or Madam,",
        "received_dated": "I received your notice dated {date}{amounts}.",
        "received": "I received your recent notice{amounts}.",
        "amounts": ", which mentions {amounts}",
        "confirm": "Before I take any action, please confirm that this notice was sent by your office and that the "
                   "details in it are correct.",
        "deadline": "The notice asks me to act by {date}. If I need more time to gather documents or arrange "
                    "payment, could you please allow an extension?",
        "plan": "If I do owe this amount, please let me know whether I can pay it in instalments through a payment "
                "plan.",
        "reference": "Please reply through your official contact details. My reference or account number is: "
                     "[reference number from the letter]",
        "closing": "Thank you,\n[Your full name]\n[Your address or phone number]",
        "recipient_none": "The office that sent the notice",
    },
    "hi": {
        "to": "सेवा में,\n{recipient}",
        "subject_dated": "विषय: आपका {date} का नोटिस",
        "subject": "विषय: आपका हाल का नोटिस",
        "greeting": "महोदय/महोदया,",
        "received_dated": "मुझे आपका {date} का नोटिस मिला है{amounts}।",
        "received": "मुझे आपका हाल का नोटिस मिला है{amounts}।",
        "amounts": ", जिसमें {amounts} की रकम लिखी है",
        "confirm": "कोई भी कदम उठाने से पहले, कृपया पुष्टि करें कि यह नोटिस आपके दफ़्तर ने ही भेजा है और इसमें दी "
                   "गई जानकारी सही है।",
        "deadline": "नोटिस में {date} तक कार्रवाई करने को कहा गया है। अगर मुझे काग़ज़ जुटाने या भुगतान का इंतज़ाम "
                    "करने के लिए और समय चाहिए, तो कृपया समय बढ़ाने पर विचार करें।",
        "plan": "अगर यह रकम मुझे सच में देनी है, तो कृपया बताएँ कि क्या मैं इसे किस्तों में चुका सकता/सकती हूँ।",
        "reference": "कृपया अपने आधिकारिक संपर्क से जवाब दें। मेरा रेफ़रेंस या खाता नंबर: "
                     "[पत्र में लिखा रेफ़रेंस नंबर]",
        "closing": "धन्यवाद,\n[आपका पूरा नाम]\n[आपका पता या फ़ोन नंबर]",
        "recipient_none": "नोटिस भेजने वाला दफ़्तर",
    },
    "es": {
        "to": "Para: {recipient}",
        "subject_dated": "Asunto: Su aviso con fecha {date}",
        "subject": "Asunto: Su aviso reciente",
        "greeting": "Estimados señores:",
        "received_dated": "He recibido su aviso con fecha {date}{amounts}.",
        "received": "He recibido su aviso reciente{amounts}.",
        "amounts": ", en el que se mencionan {amounts}",
        "confirm": "Antes de hacer nada, les ruego que me confirmen que este aviso lo envió su oficina y que los "
                   "datos que contiene son correctos.",
        "deadline": "El aviso me pide actuar antes del {date}. Si necesito más tiempo para reunir documentos u "
                    "organizar el pago, ¿podrían concederme una prórroga?",
        "plan": "Si de verdad debo esta cantidad, les agradecería saber si puedo pagarla a plazos mediante un plan "
                "de pagos.",
        "reference": "Les ruego que respondan a través de sus datos de contacto oficiales. Mi número de referencia "
                     "o de cuenta es: [número de referencia de la carta]",
        "closing": "Atentamente,\n[Su nombre completo]\n[Su dirección o teléfono]",
        "recipient_none": "La oficina que envió el aviso",
    },
}

# ---------------------------------------------------------------- glossary

# (pattern, case_sensitive, {lang: (term, meaning)}). The English term is shown next to the translation, so the
# reader can find the word in the letter.
GLOSSARY = [
    (r"\bnotices?\b|नोटिस|\baviso\b", False, {
        "en": ("Notice", "An official letter telling you about something you may need to do."),
        "hi": ("नोटिस", "आधिकारिक पत्र, जो बताता है कि आपको शायद कुछ करना है।"),
        "es": ("Aviso", "Carta oficial que le informa de algo que quizá tenga que hacer.")}),
    (r"\bintimation\b|सूचना", False, {
        "en": ("Intimation", "A formal letter that tells you about a decision, for example after your tax return "
                             "was processed."),
        "hi": ("सूचना", "औपचारिक पत्र जो किसी फ़ैसले की जानकारी देता है, जैसे आयकर रिटर्न की जाँच के बाद।"),
        "es": ("Notificación", "Carta formal que le comunica una decisión, por ejemplo después de procesar su "
                               "declaración de impuestos.")}),
    (r"\bassessment year\b|\bA\.Y\.|\bAY\s?20\d\d", False, {
        "en": ("Assessment year", "In India, the year after the financial year: the tax on income earned in "
                                  "2025-26 is worked out in assessment year 2026-27."),
        "hi": ("आकलन वर्ष (असेसमेंट ईयर)", "भारत में वित्त वर्ष के बाद वाला साल: 2025-26 में हुई कमाई पर टैक्स "
                                        "आकलन वर्ष 2026-27 में तय होता है।"),
        "es": ("Año de evaluación", "En la India, el año siguiente al año fiscal: el impuesto sobre lo ganado en "
                                    "2025-26 se calcula en el año de evaluación 2026-27.")}),
    (r"\bassess(?:ment|ed)\b|निर्धारण", False, {
        "en": ("Assessment", "The office's calculation of how much tax or charge you owe."),
        "hi": ("निर्धारण (असेसमेंट)", "दफ़्तर का यह हिसाब कि आपको कितना टैक्स या शुल्क देना है।"),
        "es": ("Liquidación", "El cálculo que hace la oficina de cuánto impuesto o cargo debe usted.")}),
    (r"\barrears?\b|बकाया", False, {
        "en": ("Arrears", "Money that was due earlier and has not been paid yet."),
        "hi": ("बकाया", "वह रकम जो पहले देनी थी और अभी तक नहीं दी गई।"),
        "es": ("Atrasos", "Dinero que debía pagarse antes y que todavía no se ha pagado.")}),
    (r"\bbalance due\b|\bamount (?:due|payable)\b|\boutstanding\b", False, {
        "en": ("Balance due", "The amount still left to pay."),
        "hi": ("देय रकम", "वह रकम जो अभी चुकानी बाक़ी है।"),
        "es": ("Saldo pendiente", "La cantidad que todavía falta por pagar.")}),
    (r"\bdue date\b|\bpayment due\b|अंतिम तिथि|fecha (?:de )?vencimiento|fecha límite", False, {
        "en": ("Due date", "The last day to pay or reply without extra charges."),
        "hi": ("अंतिम तारीख़", "बिना अतिरिक्त शुल्क के भुगतान करने या जवाब देने का आख़िरी दिन।"),
        "es": ("Fecha de vencimiento", "El último día para pagar o responder sin recargos.")}),
    (r"\boverdue\b|\bpast due\b|vencid[oa]", False, {
        "en": ("Overdue", "Past the date by which it should have been paid."),
        "hi": ("समय निकल चुका (ओवरड्यू)", "जिसका भुगतान तय तारीख़ तक हो जाना चाहिए था, पर नहीं हुआ।"),
        "es": ("Vencido", "Que ya pasó la fecha en que debía pagarse.")}),
    (r"\bpenalt(?:y|ies)\b|जुर्माना|\bmultas?\b|\bsanci[oó]n", False, {
        "en": ("Penalty", "An extra charge for breaking a rule, such as paying or filing late."),
        "hi": ("जुर्माना (पेनल्टी)", "किसी नियम को तोड़ने पर लगने वाला अतिरिक्त शुल्क, जैसे देर से भुगतान करने "
                                     "पर।"),
        "es": ("Multa o sanción", "Un cargo extra por no cumplir una norma, como pagar o presentar algo tarde.")}),
    (r"\binterest\b|ब्याज|\bintereses\b", False, {
        "en": ("Interest", "Extra money added over time to an amount that is still unpaid."),
        "hi": ("ब्याज", "बिना चुकाई रकम पर समय के साथ जुड़ने वाला अतिरिक्त पैसा।"),
        "es": ("Intereses", "Dinero extra que se suma con el tiempo a una cantidad que sigue sin pagarse.")}),
    (r"\blate (?:fee|payment (?:fee|charge))s?\b|\bsurcharge\b|\brecargos?\b|विलंब शुल्क", False, {
        "en": ("Late fee", "An extra charge added because a payment was late."),
        "hi": ("विलंब शुल्क", "देर से भुगतान करने पर जोड़ा गया अतिरिक्त शुल्क।"),
        "es": ("Recargo por demora", "Un cargo extra que se añade por pagar tarde.")}),
    (r"\bdemand notice\b|\btax demand\b|\boutstanding demand\b|\bdemand of\b", False, {
        "en": ("Demand", "An official statement that you must pay a stated amount."),
        "hi": ("माँग (डिमांड)", "आधिकारिक सूचना कि आपको एक तय रकम चुकानी है।"),
        "es": ("Requerimiento de pago", "Aviso oficial de que debe pagar una cantidad concreta.")}),
    (r"\bdisconnect(?:ion|ed)?\b|कनेक्शन काट|बिजली काट|\bcorte de (?:luz|servicio)\b", False, {
        "en": ("Disconnection", "Cutting off a service such as electricity, water or a phone line."),
        "hi": ("कनेक्शन काटना", "बिजली, पानी या फ़ोन जैसी सेवा बंद कर देना।"),
        "es": ("Corte del servicio", "Suspender un servicio como la luz, el agua o la línea telefónica.")}),
    (r"\blev(?:y|ies|ied)\b", False, {
        "en": ("Levy", "A charge an authority officially imposes. In US tax letters, a levy also means taking your "
                       "property or money to pay a tax debt."),
        "hi": ("लेवी", "किसी सरकारी संस्था का लगाया शुल्क। अमेरिका के टैक्स पत्रों में इसका मतलब टैक्स बकाया "
                       "वसूलने के लिए संपत्ति या पैसा ज़ब्त करना भी है।"),
        "es": ("Gravamen o embargo (levy)", "Un cargo que impone una autoridad. En las cartas de impuestos de "
                                            "EE. UU. también significa quitarle bienes o dinero para cobrar una "
                                            "deuda fiscal.")}),
    (r"\bgarnish(?:ment|ed|ee)?\b|embargo de (?:salario|sueldo)", False, {
        "en": ("Garnishment", "When a court or agency takes money straight from your wages or bank account to pay a "
                              "debt."),
        "hi": ("वेतन कुर्की (गार्निशमेंट)", "जब अदालत या कोई संस्था क़र्ज़ चुकाने के लिए सीधे आपकी तनख़्वाह या "
                                           "बैंक खाते से पैसा काटती है।"),
        "es": ("Embargo de salario", "Cuando un tribunal o una agencia cobra una deuda directamente de su sueldo o "
                                     "de su cuenta bancaria.")}),
    (r"\bliens?\b", False, {
        "en": ("Lien", "A legal claim on your property until a debt is paid."),
        "hi": ("ग्रहणाधिकार (लियन)", "क़र्ज़ चुकने तक आपकी संपत्ति पर क़ानूनी दावा।"),
        "es": ("Gravamen (lien)", "Un derecho legal sobre sus bienes hasta que se pague una deuda.")}),
    (r"\bappeals?\b|अपील|\bapelaci[oó]n\b|\brecurso\b", False, {
        "en": ("Appeal", "A formal request asking a higher office to review a decision."),
        "hi": ("अपील", "किसी फ़ैसले पर दोबारा विचार के लिए ऊँचे दफ़्तर से औपचारिक अनुरोध।"),
        "es": ("Apelación o recurso", "Una solicitud formal para que una oficina superior revise una decisión.")}),
    (r"\bdisputes?\b|\bdisagree\b", False, {
        "en": ("Dispute", "Telling the office you think something in the letter is wrong."),
        "hi": ("आपत्ति (डिस्प्यूट)", "दफ़्तर को बताना कि आपके हिसाब से पत्र में कुछ ग़लत है।"),
        "es": ("Reclamación", "Decirle a la oficina que usted cree que algo de la carta está mal.")}),
    (r"\bKYC\b", True, {
        "en": ("KYC", "Know Your Customer: the ID and address details a bank or phone company keeps on file."),
        "hi": ("KYC", "“अपने ग्राहक को जानें”: पहचान और पते की जानकारी जो बैंक या मोबाइल कंपनी अपने पास रखती है।"),
        "es": ("KYC", "“Conozca a su cliente”: los datos de identidad y domicilio que un banco o una compañía "
                      "telefónica guarda sobre usted.")}),
    (r"\bPAN\b", True, {
        "en": ("PAN", "Permanent Account Number: your 10-character Indian tax ID."),
        "hi": ("PAN", "स्थायी खाता संख्या: आयकर विभाग का 10 अक्षरों वाला पहचान नंबर।"),
        "es": ("PAN", "Número de cuenta permanente: su identificación fiscal india de 10 caracteres.")}),
    (r"\baadhaa?r\b|आधार", False, {
        "en": ("Aadhaar", "India's 12-digit ID number, issued by UIDAI. Never share the full number with a caller."),
        "hi": ("आधार", "UIDAI का दिया 12 अंकों का पहचान नंबर। फ़ोन करने वाले को पूरा नंबर कभी न बताएँ।"),
        "es": ("Aadhaar", "Número de identidad indio de 12 cifras, emitido por la UIDAI. Nunca dé el número completo "
                          "a quien le llame.")}),
    (r"\bTDS\b", True, {
        "en": ("TDS", "Tax Deducted at Source: tax taken out before you receive a payment such as salary or "
                      "interest."),
        "hi": ("TDS", "स्रोत पर कटौती किया गया टैक्स: तनख़्वाह या ब्याज जैसे भुगतान मिलने से पहले ही काटा गया "
                      "टैक्स।"),
        "es": ("TDS", "Impuesto retenido en origen: impuesto que se descuenta antes de recibir un pago como el sueldo "
                      "o los intereses.")}),
    (r"\bITR\b|\bincome tax return\b|आयकर रिटर्न", False, {
        "en": ("Income tax return (ITR)", "The form you file each year to report your income and tax."),
        "hi": ("आयकर रिटर्न (ITR)", "हर साल भरा जाने वाला फ़ॉर्म, जिसमें आप अपनी आय और टैक्स बताते हैं।"),
        "es": ("Declaración de la renta (ITR)", "El formulario que presenta cada año para declarar sus ingresos e "
                                                "impuestos.")}),
    (r"\brefunds?\b|रिफ़ंड|रिफंड|\breembolsos?\b", False, {
        "en": ("Refund", "Money paid back to you, for example tax you paid too much of."),
        "hi": ("रिफ़ंड", "आपको वापस किया जाने वाला पैसा, जैसे ज़्यादा भरा गया टैक्स।"),
        "es": ("Reembolso", "Dinero que se le devuelve, por ejemplo impuestos que pagó de más.")}),
    (r"\bOTP\b|ओटीपी", False, {
        "en": ("OTP", "One-Time Password: a short code sent to your phone. It is for you alone; never share it."),
        "hi": ("OTP", "वन-टाइम पासवर्ड: फ़ोन पर आने वाला छोटा कोड। यह सिर्फ़ आपके लिए है, इसे कभी किसी को न "
                      "बताएँ।"),
        "es": ("OTP", "Contraseña de un solo uso: un código corto que llega a su teléfono. Es solo para usted; no "
                      "lo comparta nunca.")}),
    (r"\bUPI\b", True, {
        "en": ("UPI", "India's system for paying from your phone (PhonePe, Google Pay, Paytm and others)."),
        "hi": ("UPI", "फ़ोन से भुगतान करने का भारतीय सिस्टम (PhonePe, Google Pay, Paytm वग़ैरह)।"),
        "es": ("UPI", "El sistema indio para pagar desde el teléfono (PhonePe, Google Pay, Paytm y otros).")}),
    (r"\bSSN\b|\bsocial security number\b", False, {
        "en": ("Social Security number (SSN)", "Your 9-digit US ID number. Keep it private."),
        "hi": ("सोशल सिक्योरिटी नंबर (SSN)", "अमेरिका का 9 अंकों का पहचान नंबर। इसे निजी रखें।"),
        "es": ("Número de Seguro Social (SSN)", "Su número de identidad de EE. UU. de 9 cifras. Manténgalo en "
                                                "privado.")}),
    (r"\binstal?lments?\b|\bpayment plan\b|\binstallment agreement\b|किस्त|\ba plazos\b", False, {
        "en": ("Payment plan", "Paying a debt in smaller parts over time, by agreement with the office."),
        "hi": ("किस्तों में भुगतान", "दफ़्तर की सहमति से बकाया रकम को छोटे-छोटे हिस्सों में चुकाना।"),
        "es": ("Plan de pagos", "Pagar una deuda en partes más pequeñas a lo largo del tiempo, de acuerdo con la "
                                "oficina.")}),
    (r"\bsummons\b|समन", False, {
        "en": ("Summons", "An official order to appear in court or at an office."),
        "hi": ("समन", "अदालत या दफ़्तर में हाज़िर होने का आधिकारिक आदेश।"),
        "es": ("Citación", "Una orden oficial para presentarse ante un tribunal o una oficina.")}),
    (r"\bwarrants?\b|वारंट", False, {
        "en": ("Warrant", "A court's written order, for example to arrest someone. Real warrants are not sent by "
                          "text and are never cancelled by a payment."),
        "hi": ("वारंट", "अदालत का लिखित आदेश, जैसे किसी की गिरफ़्तारी का। असली वारंट मैसेज से नहीं आते और पैसे "
                        "देने से रद्द नहीं होते।"),
        "es": ("Orden judicial", "Una orden escrita de un tribunal, por ejemplo de arresto. Las órdenes reales no "
                                 "llegan por mensaje y nunca se anulan con un pago.")}),
    (r"\bFIR\b", True, {
        "en": ("FIR", "First Information Report: the report the police in India write when a crime is reported."),
        "hi": ("FIR", "प्रथम सूचना रिपोर्ट: किसी अपराध की शिकायत पर पुलिस की लिखी पहली रिपोर्ट।"),
        "es": ("FIR", "Informe policial inicial: el informe que escribe la policía en la India cuando se denuncia "
                      "un delito.")}),
    (r"\bcustoms? (?:duty|charges?|clearance)\b|सीमा शुल्क|\baduanas?\b", False, {
        "en": ("Customs duty", "Tax charged on goods that come from another country."),
        "hi": ("सीमा शुल्क (कस्टम ड्यूटी)", "दूसरे देश से आने वाले सामान पर लगने वाला टैक्स।"),
        "es": ("Aranceles de aduana", "Impuesto que se cobra por productos que llegan de otro país.")}),
    (r"\bchallans?\b|चालान", False, {
        "en": ("Challan", "In India, an official slip for a fine (such as a traffic fine) or for a payment."),
        "hi": ("चालान", "जुर्माने (जैसे ट्रैफ़िक जुर्माने) या भुगतान की आधिकारिक पर्ची।"),
        "es": ("Challan", "En la India, un comprobante oficial de una multa (como una de tráfico) o de un pago.")}),
    (r"\bprima facie\b", False, {
        "en": ("Prima facie", "“At first sight”: based on a first look, before a detailed check."),
        "hi": ("प्रथम दृष्टया", "पहली नज़र में, यानी विस्तार से जाँच होने से पहले।"),
        "es": ("Prima facie", "“A primera vista”: según una primera revisión, antes de un examen detallado.")}),
    (r"\badjustments?\b", False, {
        "en": ("Adjustment", "A change the office made to the figures you gave, for example on your tax return."),
        "hi": ("समायोजन (एडजस्टमेंट)", "आपके दिए आँकड़ों में दफ़्तर का किया बदलाव, जैसे आयकर रिटर्न में।"),
        "es": ("Ajuste", "Un cambio que hizo la oficina en las cifras que usted dio, por ejemplo en su declaración "
                         "de impuestos.")}),
    (r"\bu/s\b|\bunder section\b", False, {
        "en": ("u/s", "“Under section”: the part of the law the letter relies on."),
        "hi": ("u/s", "“धारा के तहत”: क़ानून का वह हिस्सा जिसके आधार पर पत्र भेजा गया है।"),
        "es": ("u/s", "“Según la sección”: la parte de la ley en la que se basa la carta.")}),
    (r"\bcompliance\b", False, {
        "en": ("Compliance", "Following the rules, or doing what the office asked."),
        "hi": ("अनुपालन (कंप्लायंस)", "नियमों का पालन करना, या दफ़्तर ने जो कहा वह करना।"),
        "es": ("Cumplimiento", "Seguir las normas o hacer lo que pidió la oficina.")}),
    (r"\bverif(?:y|ication)\b", False, {
        "en": ("Verification", "Checking that something is true, such as your identity. Do it only on official "
                               "channels you open yourself."),
        "hi": ("सत्यापन (वेरिफ़िकेशन)", "किसी बात की सच्चाई जाँचना, जैसे आपकी पहचान। यह सिर्फ़ उन्हीं "
                                        "आधिकारिक माध्यमों से करें जिन्हें आप ख़ुद खोलें।"),
        "es": ("Verificación", "Comprobar que algo es cierto, como su identidad. Hágalo solo por canales oficiales "
                               "que usted mismo abra.")}),
    (r"\bremit(?:tance)?\b", False, {
        "en": ("Remittance", "A payment sent to someone."),
        "hi": ("प्रेषण (रेमिटेंस)", "किसी को भेजा गया भुगतान।"),
        "es": ("Remesa o pago", "Un pago enviado a alguien.")}),
    (r"\btax year\b|\bfinancial year\b|वित्त वर्ष|वित्तीय वर्ष", False, {
        "en": ("Tax year", "The 12-month period the tax is for."),
        "hi": ("वित्त वर्ष", "वह 12 महीने की अवधि जिसके लिए टैक्स लगता है।"),
        "es": ("Año fiscal", "El periodo de 12 meses al que corresponde el impuesto.")}),
    (r"\be-?filing\b", False, {
        "en": ("e-filing", "Filing forms online on the official portal."),
        "hi": ("ई-फ़ाइलिंग", "आधिकारिक पोर्टल पर ऑनलाइन फ़ॉर्म भरना।"),
        "es": ("Presentación electrónica", "Presentar formularios en línea en el portal oficial.")}),
    (r"\bcollection agency\b|\bdebt collector\b", False, {
        "en": ("Collection agency", "A company hired to collect unpaid debts."),
        "hi": ("वसूली एजेंसी", "बकाया क़र्ज़ वसूलने के लिए रखी गई कंपनी।"),
        "es": ("Agencia de cobros", "Una empresa contratada para cobrar deudas impagadas.")}),
    (r"\bIRS\b|\binternal revenue service\b", False, {
        "en": ("IRS", "Internal Revenue Service: the US federal tax office."),
        "hi": ("IRS", "इंटरनल रेवेन्यू सर्विस: अमेरिका का संघीय टैक्स विभाग।"),
        "es": ("IRS", "Servicio de Impuestos Internos: la oficina federal de impuestos de EE. UU.")}),
    (r"\bdeport(?:ation|ed)?\b", False, {
        "en": ("Deportation", "Being sent out of a country by the government. It is never decided over the phone "
                              "or cancelled by a payment."),
        "hi": ("देश से निकालना (डिपोर्टेशन)", "सरकार का किसी को देश से बाहर भेजना। यह फ़ोन पर तय नहीं होता और "
                                              "पैसे देकर रद्द नहीं होता।"),
        "es": ("Deportación", "Que el gobierno expulse a alguien del país. Nunca se decide por teléfono ni se anula "
                              "con un pago.")}),
]
_GLOSSARY = [(re.compile(p, 0 if case else re.IGNORECASE), terms) for p, case, terms in GLOSSARY]


# ---------------------------------------------------------------- building the explanation

class _Strict(dict):
    def __missing__(self, key):
        raise KeyError(f"template placeholder {{{key}}} has no value")


def _fill(template, **values):
    return template.format_map(_Strict(values))


def format_date(iso, lang):
    try:
        d = date.fromisoformat(str(iso))
    except ValueError:
        return str(iso)
    month = MONTHS[lang][d.month - 1]
    return f"{d.day} de {month} de {d.year}" if lang == "es" else f"{d.day} {month} {d.year}"


def letter_language(text):
    """"hi" for Devanagari, "es" for Spanish, else "en" (the language the reply draft is written in)."""
    text = text or ""
    letters = [c for c in text if c.isalpha()]
    if letters and sum("ऀ" <= c <= "ॿ" for c in letters) > len(letters) * 0.2:
        return "hi"
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    spanish = sum(w in {"el", "la", "los", "las", "de", "del", "que", "usted", "su", "sus", "por", "para", "pago",
                        "aviso", "cuenta", "fecha", "con", "una", "es", "y"} for w in words)
    english = sum(w in {"the", "of", "and", "to", "you", "your", "is", "for", "on", "this", "with", "by", "pay",
                        "notice", "account", "date", "a"} for w in words)
    return "es" if spanish >= 5 and spanish > english else "en"


def _official(brief, lang, short=False):
    agency = brief.get("agency") or {}
    name, phone, site = agency.get("name"), agency.get("official_phone"), agency.get("official_site")
    p = PHRASES[lang]
    if name and phone and site and not short:
        return _fill(p["official_phone_site"], agency=name, phone=phone, site=site)
    if name and phone:
        return _fill(p["official_phone"], agency=name, phone=phone)
    if name and site:
        return _fill(p["official_site"], agency=name, site=site)
    return p["official_short_none"] if short else p["official_none"]


def _report(brief, lang):
    channel = brief.get("report_channel") or {}
    p = PHRASES[lang]
    if channel.get("name") and channel.get("url") and channel.get("phone"):
        return _fill(p["report_url_phone"], name=channel["name"], url=channel["url"], phone=channel["phone"])
    if channel.get("name") and channel.get("url"):
        return _fill(p["report_url"], name=channel["name"], url=channel["url"])
    return p["report_none"]


def _lower_first(text, lang):
    return text if lang == "hi" or not text else text[0].lower() + text[1:]


_COMPUTED_LETTER = re.compile(r"^letter_date \+ (\d+) days$")
_COMPUTED_RECEIPT = re.compile(r"^date received \(taken as (\d{4}-\d{2}-\d{2})\) \+ (\d+) days$")
_GENERIC_WHAT = {"", "deadline in the letter", "respond to the letter"}


def _deadline_actions(brief, lang):
    p = PHRASES[lang]
    actions = []
    for d in brief.get("deadlines") or []:
        if not d.get("date"):
            continue
        what = (d.get("what") or "").strip()
        if len(what) >= 118 and not what.endswith((".", "!", "?", "।")):
            what += "…"  # the reader keeps the first 120 characters of the line
        how = p["deadline_plain"] if what.lower() in _GENERIC_WHAT else _fill(p["deadline_quote"], what=what)
        computed = d.get("computed_from") or ""
        m = _COMPUTED_LETTER.match(computed)
        r = _COMPUTED_RECEIPT.match(computed)
        if m:
            how += _fill(p["computed_letter"], days=m.group(1))
        elif r:
            how += _fill(p["computed_receipt"], days=r.group(2), received=format_date(r.group(1), lang))
        actions.append({"step": _fill(p["deadline_step"], date=format_date(d["date"], lang)), "how": how,
                        "by": d["date"]})
    return actions


def _jargon(letter_text, lang):
    found = []
    for pattern, terms in _GLOSSARY:
        m = pattern.search(letter_text or "")
        if m:
            found.append((m.start(), terms))
    out = []
    for _, terms in sorted(found, key=lambda item: item[0])[:MAX_JARGON]:
        term, meaning = terms[lang]
        if lang != "en":
            # "जुर्माना (Penalty)", "आयकर रिटर्न (ITR)": the local word, then the word as the letter probably has it
            english = terms["en"][0]
            acronym = re.search(r"\(([^)]+)\)", english)
            english = acronym.group(1) if acronym else english
            term = re.sub(r"\s*\([^)]*\)", "", term)
            if english.lower() != term.lower():
                term = f"{term} ({english})"
        out.append({"term": term, "meaning": meaning})
    return out


def _reply_draft(brief, letter_lang):
    r = REPLY[letter_lang]
    agency = brief.get("agency") or {}
    sender = (brief.get("claimed_sender") or "").strip()
    recipient = agency.get("name") or (sender if 0 < len(sender) <= 80 and not re.search(r"[.!?:]$", sender)
                                       else r["recipient_none"])
    letter_date = format_date(brief["letter_date"], letter_lang) if brief.get("letter_date") else None
    amounts = [a for a in brief.get("amounts") or [] if a][:2]
    amounts_clause = _fill(r["amounts"], amounts=" / ".join(amounts)) if amounts else ""
    dates = [d["date"] for d in brief.get("deadlines") or [] if d.get("date")]
    lines = [_fill(r["to"], recipient=recipient),
             _fill(r["subject_dated"], date=letter_date) if letter_date else r["subject"],
             "", r["greeting"], "",
             (_fill(r["received_dated"], date=letter_date, amounts=amounts_clause) if letter_date
              else _fill(r["received"], amounts=amounts_clause)) + " " + r["confirm"], ""]
    if dates:
        lines += [_fill(r["deadline"], date=format_date(dates[0], letter_lang)), ""]
    if amounts:
        lines += [r["plan"], ""]
    lines += [r["reference"], "", r["closing"]]
    return "\n".join(lines)


def _questions(brief, lang, verdict):
    amounts = [a for a in brief.get("amounts") or [] if a]
    dates = [d["date"] for d in brief.get("deadlines") or [] if d.get("date")]
    amount_q = _fill(AMOUNT_QUESTION[lang][0], amount=amounts[0]) if amounts else AMOUNT_QUESTION[lang][1]
    deadline_q = (_fill(DEADLINE_QUESTION[lang][0], date=format_date(dates[0], lang)) if dates
                  else DEADLINE_QUESTION[lang][1])
    return [_fill(q, amount_question=amount_q, deadline_question=deadline_q)
            for q in QUESTIONS[verdict][lang]][:MAX_QUESTIONS]


def build(letter_text, brief, lang, level="normal"):
    """The explanation fields (tldr ... reply_draft) in one of LANGS."""
    verdict = brief.get("verdict") if brief.get("verdict") in VERDICT_TEXT else "cant_tell"
    rules = [r for r in brief.get("rules") or [] if r in RULE_TEXT]
    agency = brief.get("agency") or {}
    name = agency.get("name")
    v = VERDICT_TEXT[verdict][lang]
    p = PHRASES[lang]
    official, official_short = _official(brief, lang), _official(brief, lang, short=True)
    deadlines = [d for d in brief.get("deadlines") or [] if d.get("date")]

    # tldr
    if verdict == "likely_scam":
        tldr = v["tldr"] + (_fill(v["sign"], sign=_lower_first(RULE_TEXT[rules[0]][lang]["title"], lang))
                            if rules else "")
    elif verdict == "consistent_with_genuine":
        tldr = _fill(v["tldr"], agency=name or _NO_AGENCY[lang], official_short=official_short)
    elif not name:
        tldr = v["tldr_no_agency"]
    else:
        scored = any(r not in ("unknown_contact", "injection_detected_model") for r in rules)
        tldr = _fill(v["tldr_flags"] if scored else v["tldr_plain"], agency=name)

    # explanation
    flag_points = [f"{RULE_TEXT[r][lang]['title']}{'।' if lang == 'hi' else '.'} {RULE_TEXT[r][lang]['means']}"
                   for r in dict.fromkeys(rules)]
    facts = []
    if verdict != "likely_scam":
        if deadlines:
            first = format_date(deadlines[0]["date"], lang)
            facts.append(_fill(p["one_deadline"], date=first) if len(deadlines) == 1
                         else _fill(p["many_deadlines"], n=len(deadlines), date=first))
        else:
            facts.append(p["no_deadline"])
        amounts = [a for a in brief.get("amounts") or [] if a][:3]
        if amounts:
            facts.append(_fill(p["amounts"], amounts=", ".join(amounts)))
    intro = _fill(v["intro"], agency=name or _NO_AGENCY[lang])
    limit = MAX_EXPLANATION.get(level, 6)
    note = []
    if verdict != "likely_scam" and letter_language(letter_text) != lang:
        note = [_fill(p["reply_other_language"], letter_language=p["letter_languages"][letter_language(letter_text)])]
    explanation = ([intro] + flag_points[:3] + facts)[:limit - len(v["points"]) - len(note)] + v["points"] + note

    # actions
    values = {"agency_or_office": name or _OFFICE[lang], "official": official, "report": _report(brief, lang),
              "site": agency.get("official_site") or p["site_none"]}
    standard = [{"step": _fill(step, **values), "how": _fill(how, **values), "by": None}
                for step, how in ACTIONS[verdict][lang]]
    if verdict == "consistent_with_genuine" and not deadlines:
        standard = [a for i, a in enumerate(standard) if i != 2]  # nothing to add to a calendar
    flag_actions = [{"step": RULE_TEXT[r][lang]["step"], "how": RULE_TEXT[r][lang]["how"], "by": None}
                    for r in dict.fromkeys(rules)]
    if verdict == "likely_scam":
        actions = standard + flag_actions  # a scam's deadline is part of the pressure, so it is not repeated
    else:
        actions = _deadline_actions(brief, lang) + standard + flag_actions
    seen, unique = set(), []
    for a in actions:
        if a["step"] not in seen:
            seen.add(a["step"])
            unique.append(a)

    return {
        "tldr": tldr,
        "explanation": explanation,
        "actions": unique[:MAX_ACTIONS],
        "jargon": _jargon(letter_text, lang),
        "questions_to_ask": _questions(brief, lang, verdict),
        "reply_draft": "" if verdict == "likely_scam" else _reply_draft(brief, letter_language(letter_text)),
    }


def explain(letter_text, brief, language, level="normal", *, model, started=None):
    """The /api/explain response. `brief` is pipeline._template_brief(check): verified facts only."""
    lang = resolve_language(language)
    fallback_language = lang is None
    lang = lang or "en"
    started = started if started is not None else time.perf_counter()
    body = build(letter_text, brief, lang, level)
    return {
        "language": "English" if fallback_language else str(language).strip(),
        **body,
        "meta": {"model": model, "ms": int((time.perf_counter() - started) * 1000), "input_tokens": 0,
                 "output_tokens": 0, "fallback": False, "fallback_language": fallback_language,
                 "writer": "templates"},
    }
