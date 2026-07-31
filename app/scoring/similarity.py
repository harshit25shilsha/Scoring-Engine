import math


def cosine_similarity(vec_a, vec_b) -> float:
    """Returns cosine similarity in range [-1, 1]. Handles numpy arrays or plain lists."""
    if vec_a is None or vec_b is None:
        return 0.0

    try:
        len_a = len(vec_a)
        len_b = len(vec_b)
    except TypeError:
        return 0.0

    if len_a == 0 or len_b == 0 or len_a != len_b:
        return 0.0

    dot = sum(float(a) * float(b) for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(float(a) * float(a) for a in vec_a))
    norm_b = math.sqrt(sum(float(b) * float(b) for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def similarity_to_percentage(similarity: float) -> float:
    """Maps cosine similarity [-1, 1] to a 0-100 scale, matching other score fields."""
    clamped = max(-1.0, min(1.0, similarity))
    return round(((clamped + 1) / 2) * 100, 2)