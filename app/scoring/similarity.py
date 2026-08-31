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


def blend_fallback_score(embedding_similarity: float| None, rule_score: float |None)-> float:
    """
    Combines embedding similarity with rule_score for candidates not selected
    for full LLM review. Uses a dynamic weight rather than a fixed ratio:
    embedding_similarity's influence scales with rule_score itself, so a
    candidate with strong demonstrated rule-based evidence gets meaningful
    credit for textual/semantic closeness, but a candidate with weak
    rule-based evidence can't be rescued by generic vocabulary overlap alone.

    embedding_weight ranges from 0.2 (rule_score = 0) to 0.5 (rule_score = 100).
    """
    
    if rule_score is None:
        return round(embedding_similarity or 0.0, 2)
    
    if embedding_similarity is None:
        return round(rule_score, 2)
    
    embedding_weight = 0.2 + (rule_score / 100) * 0.3
    rule_weight = 1 - embedding_weight

    return round(embedding_similarity * embedding_weight + rule_score * rule_weight, 2)