import math
import re
from collections import Counter

K1 = 1.5
B = 0.75

STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i in is it many much my of on or should that "
    "the their there this to was what when where which who why will with you your".split()
)


def tokenize(text):
    # Split course codes so "CS201" and "CS 201" both become ["cs", "201"].
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text.lower())
    return [token for token in re.findall(r"[a-z0-9]+", text) if token not in STOPWORDS]


def keyword_scores(query, documents):
    """BM25 score of each document for the query, scaled to 0..1.

    A document of average length that contains every query term once scores 1, so the score reads as the
    IDF-weighted share of the query the document covers. Query terms missing from every document still count
    towards that share, which keeps off-topic questions from scoring high on their few common words.
    """
    terms = set(tokenize(query))
    tokenized = [Counter(tokenize(document)) for document in documents]
    if not terms or not tokenized:
        return [0.0] * len(documents)
    lengths = [sum(counts.values()) for counts in tokenized]
    average_length = sum(lengths) / len(lengths) or 1
    idf = {
        term: math.log(1 + (len(tokenized) - frequency + 0.5) / (frequency + 0.5))
        for term in terms
        for frequency in [sum(1 for counts in tokenized if term in counts)]
    }
    best = sum(idf.values())
    scores = []
    for counts, length in zip(tokenized, lengths):
        norm = K1 * (1 - B + B * length / average_length)
        score = sum(idf[term] * counts[term] * (K1 + 1) / (counts[term] + norm) for term in terms if term in counts)
        scores.append(min(1.0, score / best))
    return scores
