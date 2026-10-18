"""Dependency-free, conservative matching for Vietnamese catalog queries."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Any


STOP_WORDS = {
    "shop", "oi", "cho", "minh", "em", "hoi", "co", "con", "khong", "bao",
    "nhieu", "tien", "gia", "size", "mau", "nhe", "ne", "a", "la", "voi", "ao", "quan",
}

# Aliases intentionally map only product-family language, never prices, stock or
# other commercial facts. The database remains the sole source of those facts.
SYNONYM_PHRASES = {
    "ao phong": "ao polo",
    "ao thun co tru": "ao polo",
    "ao polo": "ao polo",
    "ao so mi": "ao somi",
    "ao somi": "ao so mi",
    "so mi": "somi",
    "somi": "so mi",
    "quan sooc": "quan short",
    "quan ngan": "quan short",
}


def normalize_vietnamese(value: str) -> str:
    """Lowercase, remove Vietnamese diacritics and normalize punctuation."""
    value = (value or "").lower().replace("đ", "d")
    value = "".join(
        char for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def levenshtein_distance(left: str, right: str) -> int:
    """Compute edit distance with O(min(n, m)) memory."""
    if left == right:
        return 0
    if len(left) < len(right):
        left, right = right, left
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, 1):
        current = [left_index]
        for right_index, right_char in enumerate(right, 1):
            insertion = current[-1] + 1
            deletion = previous[right_index] + 1
            substitution = previous[right_index - 1] + (left_char != right_char)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def similarity(left: str, right: str) -> float:
    """Return normalized edit similarity in the inclusive 0..1 range."""
    longest = max(len(left), len(right))
    return 1.0 if longest == 0 else 1.0 - levenshtein_distance(left, right) / longest


def ngrams(value: str, size: int = 3) -> set[str]:
    """Build padded character n-grams for typo-tolerant phrase comparison."""
    value = f" {normalize_vietnamese(value)} "
    if len(value) <= size:
        return {value}
    return {value[index:index + size] for index in range(len(value) - size + 1)}


def ngram_similarity(left: str, right: str) -> float:
    left_set, right_set = ngrams(left), ngrams(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def expand_synonyms(value: str) -> str:
    """Append canonical aliases so existing catalog rows can be matched safely."""
    normalized = normalize_vietnamese(value)
    additions = [canonical for phrase, canonical in SYNONYM_PHRASES.items() if phrase in normalized]
    return " ".join([normalized, *additions])


@dataclass(frozen=True)
class Match:
    score: float
    product: Mapping[str, object]


class SemanticMatcher:
    """Ranks catalog rows conservatively; low-confidence input returns no match."""

    minimum_score = 0.47

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token for token in normalize_vietnamese(value).split() if len(token) > 1 and token not in STOP_WORDS}

    @staticmethod
    def _field(product: Mapping[str, Any], key: str) -> str:
        """Read equally from dicts and sqlite3.Row instances."""
        try:
            return str(product[key] or "")
        except (KeyError, IndexError):
            return ""

    def score(self, query: str, product: Mapping[str, object]) -> float:
        expanded_query = expand_synonyms(query)
        query_tokens = self._tokens(expanded_query)
        if not query_tokens:
            return 0.0

        name = self._field(product, "name")
        category = self._field(product, "category")
        sku = self._field(product, "sku")
        normalized_sku = normalize_vietnamese(sku)
        if normalized_sku and normalized_sku in normalize_vietnamese(query):
            return 1.0

        candidates = [name, category]
        best = 0.0
        for candidate in candidates:
            normalized_candidate = normalize_vietnamese(candidate)
            candidate_tokens = self._tokens(candidate)
            if not candidate_tokens:
                continue
            # A one-word category such as "nam" is descriptive but never a
            # sufficient product identity on its own.
            overlap = (
                len(query_tokens & candidate_tokens) / len(candidate_tokens)
                if len(candidate_tokens) >= 2 else 0.0
            )
            fuzzy_token = max(
                (similarity(q_token, c_token) for q_token in query_tokens for c_token in candidate_tokens
                 if len(q_token) >= 4 and len(c_token) >= 4),
                default=0.0,
            )
            phrase = ngram_similarity(expanded_query, normalized_candidate)
            # Exact tokens dominate; fuzzy-only matching must still be strong.
            candidate_score = max(overlap, fuzzy_token * 0.72, phrase * 0.68)
            best = max(best, candidate_score)
        return best

    def best_match(self, query: str, products: Iterable[Mapping[str, object]]) -> Optional[Match]:
        ranked = [Match(self.score(query, product), product) for product in products]
        if not ranked:
            return None
        best = max(ranked, key=lambda result: result.score)
        return best if best.score >= self.minimum_score else None
