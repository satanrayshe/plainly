"""Quote grounding: is a quote the model gave us really in the independently read text?

The model reads the letter image; Textract (or the user's pasted text) is a second, independent reader.
A quote counts as grounded when its normalized form appears in that text, or when a word window of the
text matches it with a difflib ratio of at least 0.85 (OCR noise, hyphenation, curly quotes).

Fuzzy matching only looks at windows near the quote's longest words, and a Reader stops fuzzy matching
once it has spent its time allowance, so a long text and many paraphrased quotes cannot stall a request.
"""
import re
import time
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher, get_close_matches

THRESHOLD = 0.85
FUZZY_BUDGET_S = 2.0
ANCHOR_WORDS = 3
MAX_WINDOWS = 12
REFINE_STARTS = 3
_SPACE = re.compile(r"\s+")


def normalize(text):
    """Casefold, unify unicode forms, turn punctuation and symbols into spaces, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text or "").casefold()
    chars = [" " if unicodedata.category(c)[0] in "PS" else c for c in text]
    return _SPACE.sub(" ", "".join(chars)).strip()


class Reader:
    """One independently read text, normalized and indexed once, checked against many quotes."""

    def __init__(self, text, fuzzy_budget_s=FUZZY_BUDGET_S):
        self.norm = normalize(text)
        self.words = self.norm.split()
        self.positions = defaultdict(list)
        for index, word in enumerate(self.words):
            self.positions[word].append(index)
        self.vocabulary = list(self.positions)
        self.fuzzy_budget_s = fuzzy_budget_s
        self.fuzzy_spent_s = 0.0
        self.out_of_time = False
        self._close = {}

    def is_grounded(self, quote):
        q = normalize(quote)
        if not q:
            return False
        if len(q) < 6:
            # Too short for fuzzy matching to mean anything; demand an exact word-bounded hit.
            return f" {q} " in f" {self.norm} "
        return self.ratio(q, normalized=True) >= THRESHOLD

    def ratio(self, quote, normalized=False):
        """Highest similarity between the quote and a similar-length word window of the text (0..1)."""
        q = quote if normalized else normalize(quote)
        if not q or not self.norm:
            return 0.0
        if q in self.norm:
            return 1.0
        if self.fuzzy_spent_s >= self.fuzzy_budget_s:
            self.out_of_time = True
            return 0.0
        started = time.perf_counter()
        try:
            return self._fuzzy(q)
        finally:
            self.fuzzy_spent_s += time.perf_counter() - started

    def _fuzzy(self, q):
        q_words = q.split()
        n = len(q_words)
        slack = max(1, round(n * 0.15))
        matcher = SequenceMatcher(None, autojunk=False)
        matcher.set_seq2(q)  # seq2 is the side difflib indexes, so keep the fixed quote there
        # Compare same-length windows first, then try longer and shorter windows at the best few starts.
        scored = sorted(((self._window_ratio(matcher, start, n, 0.0), start)
                         for start in self._candidate_starts(q_words, slack)), reverse=True)
        best = scored[0][0] if scored else 0.0
        for _, start in scored[:REFINE_STARTS]:
            for size in range(max(1, n - slack), n + slack + 1):
                if best >= 0.999:
                    return best
                best = max(best, self._window_ratio(matcher, start, size, best))
        return best

    def _window_ratio(self, matcher, start, size, floor):
        window = self.words[start:start + size]
        if not window:
            return 0.0
        matcher.set_seq1(" ".join(window))
        if matcher.real_quick_ratio() <= floor or matcher.quick_ratio() <= floor:
            return 0.0
        return matcher.ratio()

    def _candidate_starts(self, q_words, slack):
        """The few window starts worth a full comparison.

        Windows are lined up on the quote's rarest words (or near spellings of them, for OCR typos), then
        ranked by how many of the quote's words they share; only the best few are compared character by
        character.
        """
        distinct = {w for w in q_words if len(w) >= 3} or set(q_words)
        # Rarest first; a word the text lacks entirely (maybe an OCR typo) comes after the ones it has.
        anchors = sorted(distinct, key=lambda w: (len(self.positions.get(w, ())) or 10**6, -len(w)))[:ANCHOR_WORDS]
        starts = set()
        for word in anchors:
            offset = q_words.index(word)
            for position in self._positions_like(word):
                base = position - offset
                starts.update(range(max(0, base - slack), max(0, base + slack + 1)))
        starts = [s for s in starts if s < len(self.words)]
        if len(starts) <= MAX_WINDOWS:
            return sorted(starts)
        wanted = set(q_words)
        size = len(q_words)
        return sorted(starts, key=lambda s: -len(wanted.intersection(self.words[s:s + size])))[:MAX_WINDOWS]

    def _positions_like(self, word):
        if word not in self._close:
            similar = get_close_matches(word, self.vocabulary, n=3, cutoff=0.8) if len(word) >= 4 else []
            self._close[word] = sorted({word, *similar})
        return [p for w in self._close[word] for p in self.positions.get(w, ())]


def best_ratio(quote, text):
    return Reader(text).ratio(quote)


def is_grounded(quote, text):
    return Reader(text).is_grounded(quote)
