import re
import json
from collections import Counter

STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","by","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","can","need",
    "this","that","these","those","it","its","not","no","nor","so","just",
    "all","each","every","both","few","more","most","some","such","only",
    "own","same","here","there","when","where","why","how","about","into",
    "over","after","before","between","under","then","also","if","as",
    "i","me","my","we","our","you","your","they","them","their","what",
    "which","who","whom","none","very","too","up","down","out","off",
    "than","because","from","like","get","got","has","been","being",
}


def extract_heading(text):
    if not text:
        return None
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None
    first = lines[0]
    if len(first) > 100:
        return None
    if first.endswith((".", "!", "?")):
        return None
    if len(first) < 3:
        return None
    return first[:80]


def extract_concepts(text, max_concepts=4):
    if not text:
        return []
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    words = [w for w in words if w not in STOPWORDS]
    if not words:
        return []
    freqs = Counter(words)
    common = freqs.most_common(max_concepts + 4)
    concepts = []
    for word, count in common:
        if count >= 2:
            concepts.append(word)
            if len(concepts) >= max_concepts:
                break
    if not concepts:
        concepts = [common[0][0]] if common else []
    return concepts[:max_concepts]
