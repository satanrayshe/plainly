"""Template explanations (AI_MODE=off): every rule and verdict in English, Hindi and Spanish, placeholders always
filled, dates only from the verified check, and a reply draft only when the verdict isn't likely_scam."""
import itertools
import json
import re

import pytest

from conftest import BACKEND

import agencies
import explain_templates as et
import pipeline
import verifier

LANGS = {"English": "en", "Hindi": "hi", "Spanish": "es"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
PLACEHOLDER = re.compile(r"\{[a-z_]*\}")
CONTRACT_KEYS = {"language", "tldr", "explanation", "actions", "jargon", "questions_to_ask", "reply_draft", "meta"}
IRS = {"name": "Internal Revenue Service", "official_phone": "800-829-1040", "official_site": "https://www.irs.gov"}
FTC = {"name": "FTC", "url": "https://reportfraud.ftc.gov", "phone": None}
DEADLINES = [{"date": "2026-10-05", "what": "Pay the amount due of $1,284.60 by October 5, 2026",
              "computed_from": None},
             {"date": "2026-10-15", "what": "Respond within 30 days of the date of this notice",
              "computed_from": "letter_date + 30 days"},
             {"date": "2026-10-30", "what": "Deadline in the letter",
              "computed_from": "date received (taken as 2026-09-30) + 30 days"}]


def brief(verdict="cant_tell", agency=IRS, rules=(), deadlines=DEADLINES, amounts=("$1,284.60",), sender="IRS",
          letter_date="2026-09-14", channel=FTC):
    return {"verdict": verdict, "agency": agency, "rules": list(rules), "deadlines": list(deadlines),
            "amounts": list(amounts), "claimed_sender": sender, "letter_date": letter_date,
            "report_channel": channel, "headline": "h", "flags": []}


def strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings_in(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from strings_in(v)


# ---------------------------------------------------------------- the written text itself

def test_every_rule_has_text_in_every_language():
    assert set(et.RULE_TEXT) == set(verifier.RULES)
    for rule, by_lang in et.RULE_TEXT.items():
        assert set(by_lang) == set(et.LANGS), rule
        for lang, text in by_lang.items():
            assert set(text) == {"title", "means", "step", "how"}, (rule, lang)
            for key, value in text.items():
                assert value.strip() and value == value.strip(), (rule, lang, key)
                if lang == "hi":
                    assert DEVANAGARI.search(value), (rule, key)
                elif lang == "es":
                    assert value != by_lang["en"][key], (rule, key)


@pytest.mark.parametrize("table", ["VERDICT_TEXT", "ACTIONS", "QUESTIONS"])
def test_every_verdict_has_text_in_every_language(table):
    data = getattr(et, table)
    assert set(data) == set(verifier.VERDICTS)
    for verdict, by_lang in data.items():
        assert set(by_lang) == set(et.LANGS)
        shapes = {lang: json.dumps(value, ensure_ascii=False).count('"') for lang, value in by_lang.items()}
        assert len(set(shapes.values())) == 1, (table, verdict, shapes)  # same structure in every language
        for value in strings_in(by_lang):
            assert value.strip(), (table, verdict)


def test_phrase_tables_have_the_same_keys_in_every_language():
    for table in (et.PHRASES, et.REPLY):
        assert set(table) == set(et.LANGS)
        assert table["en"].keys() == table["hi"].keys() == table["es"].keys()
        assert all(v for lang in et.LANGS for v in strings_in(table[lang]))


def test_glossary_has_about_forty_terms_in_three_languages():
    assert len(et.GLOSSARY) >= 40
    for pattern, _case, terms in et.GLOSSARY:
        re.compile(pattern)
        assert set(terms) == set(et.LANGS)
        for lang, (term, meaning) in terms.items():
            assert term.strip() and meaning.strip(), pattern
            if lang == "hi":
                assert DEVANAGARI.search(meaning), pattern


@pytest.mark.parametrize("requested, code", [
    ("English", "en"), ("english", "en"), ("Hindi", "hi"), ("हिन्दी", "hi"), ("हिंदी", "hi"), ("Spanish", "es"),
    ("Español", "es"), ("espanol", "es"), ("Tamil", None), ("Português do Brasil", None), ("", None),
])
def test_resolve_language(requested, code):
    assert et.resolve_language(requested) == code


# ---------------------------------------------------------------- built explanations

CASES = list(itertools.product(
    verifier.VERDICTS,
    [IRS, {"name": "Income Tax Department", "official_phone": None, "official_site": "https://www.incometax.gov.in"},
     None],
    [(), ("payment_gift_card", "threat_arrest", "secrecy"), ("unknown_contact",), tuple(verifier.RULES)],
    [DEADLINES, []],
    [("$1,284.60", "₹ 4,200"), ()],
))


@pytest.mark.parametrize("language", LANGS)
def test_every_combination_is_complete_and_filled(language):
    for verdict, agency, rules, deadlines, amounts in CASES:
        if verdict == "consistent_with_genuine" and (agency is None or rules not in ((), ("unknown_contact",))):
            continue  # the verifier never produces these
        for channel in (FTC, {"name": "Report Fraud", "url": "https://www.reportfraud.police.uk",
                               "phone": "0300 123 2040"}, None):
            b = brief(verdict, agency, rules, deadlines, amounts, channel=channel)
            for level in ("simple", "normal"):
                out = et.explain("Notice: pay the penalty and interest. KYC PAN Aadhaar.", b, language, level,
                                 model="rules-vtest")
                where = (verdict, agency and agency["name"], rules, bool(deadlines), amounts, level)
                assert set(out) == CONTRACT_KEYS, where
                assert out["language"] == language
                for value in strings_in({k: v for k, v in out.items() if k != "meta"}):
                    assert not PLACEHOLDER.search(value), (where, value)
                    assert "None" not in value, (where, value)
                assert out["tldr"].strip()
                assert 3 <= len(out["explanation"]) <= et.MAX_EXPLANATION[level], where
                assert all(p.strip() for p in out["explanation"])
                assert 1 <= len(out["actions"]) <= 8
                for action in out["actions"]:
                    assert action["step"].strip() and action["how"].strip(), where
                    assert action["by"] in {None} | {d["date"] for d in deadlines}, where
                assert len({a["step"] for a in out["actions"]}) == len(out["actions"])
                assert out["questions_to_ask"] and all(q.strip() for q in out["questions_to_ask"])
                if LANGS[language] == "hi":
                    assert DEVANAGARI.search(out["tldr"]) and all(DEVANAGARI.search(a["step"]) or "2026" in a["step"]
                                                                  for a in out["actions"])


def test_scam_gets_no_reply_and_no_deadline_actions():
    for language in LANGS:
        out = et.explain("Pay by gift card today", brief("likely_scam", rules=["payment_gift_card"]), language,
                         model="m")
        assert out["reply_draft"] == ""
        assert all(a["by"] is None for a in out["actions"])
        assert out["actions"][0]["step"] == et.ACTIONS["likely_scam"][LANGS[language]][0][0]


@pytest.mark.parametrize("verdict", ["consistent_with_genuine", "cant_tell"])
def test_reply_draft_is_filled_from_the_check(verdict):
    out = et.explain("Internal Revenue Service notice", brief(verdict), "Hindi", model="m")
    draft = out["reply_draft"]
    assert draft.startswith("To: Internal Revenue Service")  # an English letter gets an English reply
    assert "14 September 2026" in draft and "$1,284.60" in draft and "5 October 2026" in draft
    assert not PLACEHOLDER.search(draft) and "None" not in draft
    assert "[Your full name]" in draft  # the one thing only the reader can fill in
    assert any("अंग्रेज़ी" in point for point in out["explanation"])  # says why the draft is in English


def test_reply_draft_without_facts_still_reads_well():
    b = brief("cant_tell", agency=None, deadlines=[], amounts=(), sender="", letter_date=None)
    for language, start in (("English", "To: The office that sent the notice"),):
        draft = et.explain("some text", b, language, model="m")["reply_draft"]
        assert draft.startswith(start) and "Subject: Your recent notice" in draft
        assert "act by" not in draft and "instalments" not in draft


def test_reply_draft_follows_the_letters_language():
    hindi_letter = "बिजली विभाग\nआपका बिल बकाया है। कृपया 15-10-2026 तक भुगतान करें। जुर्माना लगेगा।"
    spanish_letter = ("Aviso de pago. Usted tiene un saldo pendiente con la oficina. La fecha límite para el pago es "
                      "el 15 de octubre. Por favor pague su cuenta para evitar recargos.")
    b = brief("cant_tell", agency=None, sender="बिजली विभाग")
    assert et.explain(hindi_letter, b, "English", model="m")["reply_draft"].startswith("सेवा में,\nबिजली विभाग")
    assert et.explain(spanish_letter, brief("cant_tell"), "English", model="m")["reply_draft"].startswith(
        "Para: Internal Revenue Service")
    jargon = [j["term"] for j in et.explain(hindi_letter, b, "Hindi", model="m")["jargon"]]
    assert "बकाया (Arrears)" in jargon and "जुर्माना (Penalty)" in jargon


def test_dates_are_written_for_each_language():
    assert et.format_date("2026-10-05", "en") == "5 October 2026"
    assert et.format_date("2026-10-05", "hi") == "5 अक्टूबर 2026"
    assert et.format_date("2026-10-05", "es") == "5 de octubre de 2026"


def test_computed_deadlines_are_explained():
    out = et.explain("x", brief("consistent_with_genuine"), "Spanish", model="m")
    hows = [a["how"] for a in out["actions"] if a["by"]]
    assert "30 días después de la fecha de la carta" in hows[1]
    assert "30 de septiembre de 2026" in hows[2] and "Busque en la carta" in hows[2]


def test_unsupported_language_falls_back_to_english():
    out = et.explain("x", brief(), "Tamil", model="rules-vx")
    assert out["language"] == "English" and out["meta"]["fallback_language"] is True
    assert out["meta"]["fallback"] is False and out["meta"]["model"] == "rules-vx"
    assert out["tldr"] == et.explain("x", brief(), "English", model="m")["tldr"]


def test_jargon_is_found_in_order_and_case_rules_hold():
    text = "Your PAN and KYC must be updated. The pan is hot. Penalty and interest apply. Aadhaar linked."
    terms = [j["term"] for j in et.explain(text, brief(), "English", model="m")["jargon"]]
    assert terms[:5] == ["PAN", "KYC", "Penalty", "Interest", "Aadhaar"]
    assert [j["term"] for j in et.explain("a frying pan", brief(), "English", model="m")["jargon"]] == []
    assert len(et.explain(" ".join(p for p, _, _ in et.GLOSSARY), brief(), "English", model="m")["jargon"]) <= 8


# ---------------------------------------------------------------- through the pipeline, on real letters

def _texts():
    root = BACKEND.parent
    out = [p.read_text(encoding="utf-8") for p in sorted((root / "samples" / "letters").glob("*.txt"))]
    out += [json.loads(p.read_text(encoding="utf-8"))["text"] for p in sorted((root / "eval" / "dev").glob("*.json"))]
    return out


def test_every_dev_and_sample_letter_explains_in_three_languages():
    registry = agencies.load_registry(BACKEND / "registry.json")
    for text in _texts():
        check = pipeline.check_request(pipeline.parse_check_request({"text": text}), registry=registry)
        letter_text = check.pop("letter_text")
        for language in LANGS:
            out = pipeline.narrate(letter_text, check, language, "simple")
            assert (out["reply_draft"] == "") == (check["verdict"] == "likely_scam")
            dumped = json.dumps(out, ensure_ascii=False)
            assert not PLACEHOLDER.search(dumped.replace('"meta"', "")), language
            assert "ignore previous instructions" not in dumped.lower()
            allowed = {d["date"] for d in check["extracted"]["deadlines"]}
            assert all(a["by"] is None or a["by"] in allowed for a in out["actions"])
