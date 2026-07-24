import re


def _normalize(text: str) -> str:
    return text.lower().strip()


def _extract_alternatives(skill_phrase: str) -> list[str]:
    
    base = re.sub(r"\(.*?\)", "", skill_phrase).strip()
    tokens = [base] if base else []

    paren_match = re.search(r"\((.*?)\)", skill_phrase)
    if paren_match:
        inner = paren_match.group(1)
        inner = re.sub(r"\bor\b|\band\b", ",", inner, flags=re.IGNORECASE)
        parts = [p.strip() for p in inner.split(",") if p.strip()]
        tokens.extend(parts)

    return [_normalize(t) for t in tokens if t]


def _skill_matches(candidate_skills: list[str], required_skill: str) -> bool:
    candidate_norm = [_normalize(s) for s in candidate_skills]
    alternatives = _extract_alternatives(required_skill)

    for alt in alternatives:
        for cand in candidate_norm:
            if alt in cand or cand in alt:
                return True
    return False


def score_skills(candidate_skills: list[str], required_skills: list[str]) -> dict:
    if not required_skills:
        return {"score": 100.0, "matched": [], "missing": []}

    matched, missing = [], []
    for skill in required_skills:
        if _skill_matches(candidate_skills, skill):
            matched.append(skill)
        else:
            missing.append(skill)

    score = (len(matched) / len(required_skills)) * 100
    return {"score": round(score, 2), "matched": matched, "missing": missing}


def score_experience(
    candidate_years: float | None,
    min_years: float | None,
    max_years: float | None,
) -> float:
    if min_years is None:
        return 100.0
    if candidate_years is None:
        return 50.0  # unverifiable, neutral-low score rather than fabricating certainty

    if candidate_years >= min_years and (max_years is None or candidate_years <= max_years):
        return 100.0

    if candidate_years < min_years:
        shortfall = min_years - candidate_years
        return max(0.0, 100 - shortfall * 20)

    # overqualified case
    excess = candidate_years - max_years
    return max(0.0, 100 - excess * 10)


def score_education(candidate_education: list[dict], required_education: list[str]) -> float:
    if not required_education:
        return 100.0
    if not candidate_education:
        return 40.0  # can't verify, partial credit rather than zero

    candidate_degrees = [_normalize(e.get("degree", "")) for e in candidate_education]

    for requirement in required_education:
        req_norm = _normalize(requirement)
        for degree in candidate_degrees:
            if req_norm in degree or degree in req_norm:
                return 100.0

    return 40.0  # heuristic partial credit — real equivalence checking needs semantic step


def score_location(
    candidate_city: str | None, candidate_state: str | None, candidate_country: str | None,
    job_city: str | None, job_state: str | None, job_country: str | None,
    job_location_text: str | None, work_type: str | None,
) -> float:
    combined_location_text = f"{job_location_text or ''} {work_type or ''}".lower()
    if "remote" in combined_location_text:
        return 100.0

    def norm(v):
        return (v or "").strip().lower()

    if norm(candidate_city) and norm(candidate_city) == norm(job_city):
        return 100.0
    if norm(candidate_state) and norm(candidate_state) == norm(job_state):
        return 70.0
    if norm(candidate_country) and norm(candidate_country) == norm(job_country):
        return 50.0
    if not any([candidate_city, candidate_state, candidate_country, job_city, job_state, job_country]):
        return 50.0  # no data to compare either side, neutral

    return 30.0