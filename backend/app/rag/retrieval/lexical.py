from .query import query_terms, symbol_matches
from collections import Counter
import math
import re
from backend.app.rag.ingestion.normalization import search_normalize


def tokens(text):
    return re.findall(r'[\u0621-\u064a]+|[a-z0-9]+', search_normalize(text).lower())


class BM25:
    def __init__(self, chunks, k1=1.5, b=.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.documents = [Counter(t for word in tokens(' '.join(filter(None, [c.symbol, c.section, c.text]))) for t in (query_terms(word) or {word})) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.documents]
        self.average = sum(self.lengths) / max(1, len(chunks))
        self.df = Counter(t for d in self.documents for t in d)

    def search(self, query, allowed=None):
        terms = query_terms(query); results = []
        for i, document in enumerate(self.documents):
            if allowed is not None and i not in allowed:
                continue
            score = 0.0
            for term in terms:
                tf = document.get(term, 0)
                if tf:
                    idf = math.log(1 + (len(self.documents) - self.df[term] + .5) / (self.df[term] + .5))
                    score += idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / max(self.average, 1)))
            symbol_terms = tokens(self.chunks[i].symbol or '')
            exact = symbol_matches(query, self.chunks[i].symbol)
            if exact:
                score += 2.0  # Explicit, inspectable exact-symbol bonus; not a probability.
            if score > 0:
                results.append((i, score))
        return sorted(results, key=lambda row: (-row[1], self.chunks[row[0]].id))


def rrf(rankings, constant=60):
    scores = Counter()
    for ranking in rankings:
        for rank, (index, _) in enumerate(ranking, 1):
            scores[index] += 1 / (constant + rank)
    return sorted(scores.items(), key=lambda row: (-row[1], row[0]))
