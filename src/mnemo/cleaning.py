from collections import Counter


def find_repeated_fragments(texts, min_occurrences=10, max_words=8):
    """Find short lines that repeat suspiciously often — footers, watermarks, page headers."""
    fragment_counts = Counter()
    for text in texts:
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            word_count = len(line.split())
            if 0 < word_count <= max_words:
                fragment_counts[line] += 1

    return {
        frag
        for frag, count in fragment_counts.items()
        if count >= min_occurrences
    }


def is_structural_noise(line):
    """Lines that are noise by structure regardless of frequency."""
    stripped = line.strip()
    if len(stripped) <= 2:
        return True
    if stripped.isdigit():
        return True
    if all(not c.isalnum() for c in stripped):
        return True
    return False


def clean_text(text, noise_fragments):
    """Strip noise lines from text. Returns empty string if all lines stripped."""
    lines = text.strip().split("\n")
    cleaned = []
    for line in lines:
        s = line.strip()
        if s in noise_fragments:
            continue
        if is_structural_noise(s):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def clean_pages(pages, min_occurrences=10, max_words=8):
    """Clean page texts by detecting and removing repeated noise fragments.

    Pages is a list of dicts with at least {'text': str}. Returns the
    noise set for inspection; modifies pages in-place.
    """
    page_texts = [p["text"] for p in pages]
    noise = find_repeated_fragments(page_texts, min_occurrences, max_words)
    for page in pages:
        page["text"] = clean_text(page["text"], noise)
    return noise
