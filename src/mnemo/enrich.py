import re
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

# Structural/document words that appear in headers/footers but aren't content
STRUCTURAL_WORDS = {
    "chapter","chapters","edition","editions","book","books","page","pages",
    "figure","figures","table","tables","section","sections","appendix",
    "index","preface","introduction","contents","content","copyright",
    "published","publisher","author","authors","title","review",
    "example","examples","exercise","exercises","problem","problems",
    "solution","solutions","answer","answers","question","questions",
    "reference","references","bibliography","notes","note","summary",
    "overview","conclusion","conclusions","part","parts",
    "unit","units","lesson","lessons","topic","topics","list","lists",
    "item","items","equation","equations",
    "algorithm","algorithms","property","properties","definition",
    "definitions","theorem","theorems","lemma","corollary","proof",
    "proposition","remark","remarks","tip","tips","warning","warnings",
    "caution","important","following","follows","shown","shows",
    "given","gives","called","known","defined","describe","describes",
    "discuss","discusses","explain","explains","illustrate","illustrates",
    "provide","provides","require","requires","consider","considers",
    "contain","contains","include","includes","consist","consists",
    "comprise","comprises","various","different","multiple",
    "several","specific","general","common","typical","usual",
    "previous","earlier","later","above","below",
    "without","within","through","during","since","until","while",
    "because","though","although","unless","whereas",
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

    words_lower = text.lower()
    bigrams = re.findall(r"\b([a-zA-Z]{3,})\s+([a-zA-Z]{3,})\b", words_lower)
    single_words = re.findall(r"\b[a-zA-Z]{3,}\b", words_lower)

    # Filter single words: >= 4 chars, not stopwords or structural
    filtered = [
        w for w in single_words
        if len(w) >= 4
        and w not in STOPWORDS
        and w not in STRUCTURAL_WORDS
    ]

    # Extra generic words to exclude from concepts
    GENERIC_WORDS = {"data","using","based","used","also","set","way","ways",
                     "make","shown","value","values","type","types","part",
                     "term","terms","case","cases","field","fields","form",
                     "forms","line","lines","step","steps","process","method",
                     "following","different","example","show","note","result",
                     "results","system","systems","function","functions",
                     "number","numbers","point","points","level","levels",
                     "simple","complex","possible","generally","therefore",
                     "often"}

    filtered = [w for w in filtered if w not in GENERIC_WORDS]

    # Score bigrams by combined frequency of their component words
    word_freqs = Counter(filtered)
    bigram_scores = []
    for a, b in bigrams:
        if (a not in STOPWORDS and b not in STOPWORDS
                and a not in STRUCTURAL_WORDS and b not in STRUCTURAL_WORDS
                and a not in GENERIC_WORDS and b not in GENERIC_WORDS
                and len(a) >= 3 and len(b) >= 3):
            score = word_freqs.get(a, 0) + word_freqs.get(b, 0)
            bigram_scores.append((f"{a} {b}", score))
    bigram_scores.sort(key=lambda x: -x[1])

    concepts = []
    for bg, _ in bigram_scores:
        concepts.append(bg)
        if len(concepts) >= max_concepts:
            return concepts[:max_concepts]

    # Fill remaining with frequent single words
    for word, count in word_freqs.most_common(max_concepts * 2):
        if count >= 2 or not concepts:
            concepts.append(word)
            if len(concepts) >= max_concepts:
                break

    return concepts[:max_concepts]
