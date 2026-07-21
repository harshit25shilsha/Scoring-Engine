import re


def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    text = raw_text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()