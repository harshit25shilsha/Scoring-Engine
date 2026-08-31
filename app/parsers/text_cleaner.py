import re


def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    text = raw_text.replace("\x00", "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)  # strip other control chars, keep \n and \t
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()


def prepare_for_llm(text: str, max_chars: int = 24000) -> str:
    """Bound model input while retaining both document headers and skill sections."""
    if len(text) <= max_chars:
        return text
    head_chars = max_chars * 2 // 3
    tail_chars = max_chars - head_chars
    return f"{text[:head_chars]}\n\n[...middle omitted...]\n\n{text[-tail_chars:]}"