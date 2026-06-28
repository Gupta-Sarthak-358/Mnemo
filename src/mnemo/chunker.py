MIN_PARAGRAPH_WORDS = 60


def chunk_text(text, base_chunk_index=0):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    merged = []
    buffer = ""
    for para in paragraphs:
        word_count = len(para.split())
        if word_count < MIN_PARAGRAPH_WORDS and buffer:
            buffer += "\n\n" + para
        else:
            if buffer:
                merged.append(buffer)
            buffer = para
    if buffer:
        merged.append(buffer)

    chunks = []
    for i, para in enumerate(merged):
        prev = merged[i - 1] if i > 0 else ""
        next_ = merged[i + 1] if i < len(merged) - 1 else ""
        neighbor_text = "\n\n".join(filter(None, [prev, para, next_]))
        chunks.append({
            "text": neighbor_text,
            "core_paragraph": para,
            "chunk_index": base_chunk_index + i,
        })
    return chunks
