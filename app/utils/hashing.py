import hashlib


def hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()