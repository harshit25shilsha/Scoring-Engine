import hashlib


def hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def hash_text(text: str)-> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()