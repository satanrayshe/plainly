"""Quote grounding: is a quote the model gave us really in the independently read text?

The model reads the letter image; Textract (or the user's pasted text) is a second, independent reader.
A quote counts as grounded when its normalized form appears in that text, or when a word window of the
text matches it with a difflib ratio of at least 0.85 (OCR noise, hyphenation, curly quotes).
"""
import re
import unicodedata
from difflib import SequenceMatcher

THRESHOLD = 0.85
_SPACE = re.compile(r"\s+")


def normalize(text):
    """Casefold, unify unicode forms, turn punctuation and symbols into spaces, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text or "").casefold()
    chars = [" " if unicodedata.category(c)[0] in "PS" else c for c in text]
    return _SPACE.sub(" ", "".join(chars)).strip()


def best_ratio(quote, text):
    """Highest similarity between the quote and any similar-length word window of text (0..1)."""
    q = normalize(quote)
    t = normalize(text)
    if not q or not t:
        return 0.0
    if q in t:
        return 1.0
    q_words = q.split()
    t_words = t.split()
    n = len(q_words)
    slack = max(1, round(n * 0.15))
    matcher = SequenceMatcher(None, autojunk=False)
    matcher.set_seq2(q)  # seq2 is the side difflib indexes, so keep the fixed quote there
    best = 0.0
    for size in range(max(1, n - slack), n + slack + 1):
        for start in range(0, max(1, len(t_words) - size + 1)):
            matcher.set_seq1(" ".join(t_words[start:start + size]))
            if matcher.real_quick_ratio() <= best or matcher.quick_ratio() <= best:
                continue
            best = max(best, matcher.ratio())
            if best >= 0.999:
                return best
    return best


def is_grounded(quote, text):
    q = normalize(quote)
    if not q:
        return False
    if len(q) < 6:
        # Too short for fuzzy matching to mean anything; demand an exact word-bounded hit.
        return f" {q} " in f" {normalize(text)} "
    return best_ratio(quote, text) >= THRESHOLD
