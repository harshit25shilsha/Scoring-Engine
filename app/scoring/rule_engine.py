import re
from typing import Any


def _normalize(text: Any) -> str:
    if text is None:
        return ""
    return str(text).lower().strip()


def _extract_alternatives(skill_phrase: str) -> list[str]:
    skill_phrase = _normalize(skill_phrase)
    if not skill_phrase:
        return []
    
    base = re.sub(r"\(.*?\)", "", skill_phrase).strip()
    tokens = [base] if base else []

    paren_match = re.search(r"\((.*?)\)", skill_phrase)
    if paren_match:
        inner = paren_match.group(1)
        inner = re.sub(r"\bor\b|\band\b", ",", inner, flags=re.IGNORECASE)
        parts = [p.strip() for p in inner.split(",") if p.strip()]
        tokens.extend(parts)

    return [_normalize(t) for t in tokens if t]


# Skill context categories to help disambiguate tool usage
# Maps skill patterns to their typical role contexts
SKILL_CONTEXTS = {
    "devops_infrastructure": {
        "patterns": ["kubernetes", "docker", "terraform", "cloudformation", "ansible", "chef", "puppet",
                     "aws", "azure", "gcp", "google cloud", "infrastructure", "iac", "container"],
        "supporting_indicators": ["docker", "kubernetes", "terraform", "aws", "azure", "gcp", "helm", "istio"]
    },
    "cicd_platform": {
        "patterns": ["jenkins", "gitlab", "github actions", "circleci", "travis", "bitbucket", "bamboo",
                     "azure devops", "pipeline", "ci/cd"],
        "supporting_indicators": ["jenkins", "gitlab", "github actions", "circleci", "travis", "bitbucket", "azure devops"]
    },
    "qa_automation": {
        "patterns": ["selenium", "pytest", "robot framework", "playwright", "cypress", "testng", "junit",
                     "behave", "cucumber", "manual testing", "functional testing", "regression testing"],
        "supporting_indicators": ["selenium", "pytest", "robot framework", "playwright", "cypress", "testng"]
    },
    "devops_monitoring": {
        "patterns": ["prometheus", "grafana", "datadog", "dynatrace", "elk", "splunk", "newrelic",
                     "cloudwatch", "monitoring", "logging", "observability"],
        "supporting_indicators": ["prometheus", "grafana", "datadog", "dynatrace", "elk", "splunk"]
    },
    "general_programming": {
        "patterns": ["python", "java", "go", "rust", "bash", "powershell", "ruby", "node", "nodejs", 
                     "javascript", "typescript", "c++", "c#", "scala", "groovy"],
        "supporting_indicators": []  # context-dependent; use presence of other skill categories
    }
}


def _infer_skill_context(skill_name: str, candidate_skills: list[str]) -> str | None:
    """
    Infer the context/category of a skill based on surrounding skills in the candidate's list.
    Returns the primary context if detectable, else None.
    """
    skill_norm = _normalize(skill_name)
    candidate_norm = [_normalize(s) for s in candidate_skills if _normalize(s)]
    
    # Check which context categories are represented in the candidate's skills
    context_scores = {}
    for context, indicators in SKILL_CONTEXTS.items():
        supporting = [ind for ind in indicators["supporting_indicators"] if any(ind in c for c in candidate_norm)]
        context_scores[context] = len(supporting)
    
    # Find the context with the most supporting indicators (excluding generic programming)
    main_contexts = [(c, s) for c, s in context_scores.items() if c != "general_programming" and s > 0]
    if main_contexts:
        return max(main_contexts, key=lambda x: x[1])[0]
    return None


def _skill_matches(candidate_skills: list[str], required_skill: str) -> bool:
    candidate_norm = [_normalize(s) for s in candidate_skills if _normalize(s)]
    alternatives = _extract_alternatives(required_skill)

    for alt in alternatives:
        for cand in candidate_norm:
            if _tokens_match(alt, cand):
                # Token matches — but for tools that have context ambiguity, 
                # verify the surrounding context makes sense
                required_norm = _normalize(required_skill)
                
                # If this is a CI/CD or DevOps-specific skill, check surrounding context
                if any(pattern in alt for pattern in ["jenkins", "gitlab", "github actions", "circleci", "kubernetes", "docker", "terraform"]):
                    candidate_context = _infer_skill_context(cand, candidate_skills)
                    
                    # If required skill is CI/CD-related but candidate's context is QA, reject the match
                    if any(p in required_norm for p in ["ci/cd", "pipeline", "jenkins", "gitlab", "github actions", "circleci"]):
                        if candidate_context == "qa_automation":
                            continue  # Skip this match; context mismatch
                    
                    # If required skill is DevOps infrastructure but candidate is using it for QA, reject
                    if any(p in required_norm for p in ["infrastructure", "kubernetes", "docker", "terraform", "iac"]):
                        if candidate_context == "qa_automation":
                            continue  # Skip this match; context mismatch
                
                return True
    return False


def _tokens_match(alt: str, cand: str) -> bool:
    """
    Exact match, or one is a whole-word-bounded substring of the other —
    e.g. 'react' matches inside 'react native' (word boundary respected),
    but 'java' does NOT match inside 'javascript' (no word boundary there).
    """
    if alt == cand:
        return True

    # word-boundary-aware substring check using regex, not raw `in`
    pattern = r'\b' + re.escape(alt) + r'\b'
    if re.search(pattern, cand):
        return True

    pattern = r'\b' + re.escape(cand) + r'\b'
    if re.search(pattern, alt):
        return True

    return False


def score_skills(
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str] | None = None,
    extraction_uncertain: bool = False,
) -> dict:
    required_skills = [skill for skill in required_skills if _normalize(skill)]
    preferred_skills = [skill for skill in (preferred_skills or []) if _normalize(skill)]

    if not required_skills:
        if extraction_uncertain:
            return {"score": 50.0, "matched": [], "missing": [], "matched_preferred": [], "confidence": "low_extraction"}
        return {"score": 100.0, "matched": [], "missing": [], "matched_preferred": [], "confidence": "no_requirement_stated"}

    matched, missing = [], []
    for skill in required_skills:
        if _skill_matches(candidate_skills, skill):
            matched.append(skill)
        else:
            missing.append(skill)

    base_score = (len(matched) / len(required_skills)) * 100

    # Preferred skills contribute a smaller bonus, rewarding candidates who
    # exceed the stated requirements without letting bonus skills alone
    # inflate a genuinely weak required-skill match.
    preferred_bonus = 0.0
    matched_preferred = []
    if preferred_skills:
        matched_preferred = [s for s in preferred_skills if _skill_matches(candidate_skills, s)]
        preferred_bonus = (len(matched_preferred) / len(preferred_skills)) * 15  # up to 15 bonus points

    score = min(100.0, base_score + preferred_bonus)

    return {
        "score": round(score, 2),
        "matched": matched,
        "missing": missing,
        "matched_preferred": matched_preferred,
        "confidence": "matched",
    }

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
        return max(0.0, 100 - shortfall * 30)

    # overqualified case
    excess = candidate_years - max_years
    return max(0.0, 100 - excess * 10)


def score_education(candidate_education: list[dict], required_education: list[str]) -> float:
    required_education = [requirement for requirement in required_education if _normalize(requirement)]
    if not required_education:
        return 100.0
    if not candidate_education:
        return 40.0  # can't verify, partial credit rather than zero

    candidate_degrees = [
        _normalize(e.get("degree", "") if isinstance(e, dict) else e)
        for e in candidate_education
    ]
    candidate_degrees = [degree for degree in candidate_degrees if degree]

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
    
    # For ONSITE roles, same-country-different-city is a much weaker signal
    # than for REMOTE roles. Geographic proximity matters more for on-site work.
    is_onsite = work_type and "onsite" in work_type.lower()
    if norm(candidate_country) and norm(candidate_country) == norm(job_country):
        return 30.0 if is_onsite else 50.0
    if not any([candidate_city, candidate_state, candidate_country, job_city, job_state, job_country]):
        return 30.0 if is_onsite else 50.0  # no data to compare either side

    return 20.0 if is_onsite else 30.0
