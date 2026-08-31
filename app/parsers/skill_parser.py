import re
from collections.abc import Iterable

# Canonical names are returned so resume/JD variants compare consistently.
SKILL_ALIASES = {
    "amazon web services": "AWS",
    "aws": "AWS",
    "google cloud platform": "GCP",
    "google cloud": "GCP",
    "gcp": "GCP",
    "microsoft azure": "Azure",
    "azure": "Azure",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "reactjs": "React",
    "react.js": "React",
    "react": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "py": "Python",
    "python": "Python",
    "c sharp": "C#",
    "c#": "C#",
    "c plus plus": "C++",
    "c++": "C++",
    "dotnet": ".NET",
    ".net": ".NET",
    "ci/cd": "CI/CD",
    "ci cd": "CI/CD",
    "continuous integration": "CI/CD",
    "continuous delivery": "CI/CD",
    "machine learning": "Machine Learning",
    "artificial intelligence": "Artificial Intelligence",
    "natural language processing": "NLP",
    "rest api": "REST API",
    "restful api": "REST API",
    "rest": "REST API",
    "graphql": "GraphQL",
    "sql": "SQL",
    "nosql": "NoSQL",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "scikit learn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "terraform": "Terraform",
    "jenkins": "Jenkins",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "gitlab": "GitLab",
    "apache spark": "Apache Spark",
    "spark": "Apache Spark",
    "apache kafka": "Apache Kafka",
    "kafka": "Apache Kafka",
}

KNOWN_SKILLS = {
    **SKILL_ALIASES,
    **{name.lower(): name for name in [
        "Airflow", "Ansible", "Angular", "Bash", "Cassandra", "Celery", "CircleCI",
        "Cypress", "Django", "Elasticsearch", "Excel", "FastAPI", "Flask", "Git",
        "Grafana", "Helm", "Java", "Jira", "JUnit", "Linux", "MySQL", "NumPy",
        "Pandas", "PHP", "Playwright", "Prometheus", "PyTest", "Redis", "Ruby",
        "Rust", "Selenium", "Tableau", "TensorFlow", "PyTorch", "Vite", "Vue.js",
        "Webpack", "Windows", "WordPress", "XML", "YAML", "HTML", "CSS", "GitHub",
    ]},
}


def normalize_skill(value: object) -> str:
    """Normalize spelling and separators without making Java match JavaScript."""
    if value is None:
        return ""
    text = str(value).casefold().strip()
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s*\+\s*", "+", text)
    text = re.sub(r"\s*#\s*", "#", text)
    text = re.sub(r"[.,]$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def canonical_skill(value: object) -> str:
    normalized = normalize_skill(value)
    return SKILL_ALIASES.get(normalized, KNOWN_SKILLS.get(normalized, str(value).strip() if value else ""))


def merge_skills(*skill_lists: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for skills in skill_lists:
        if not skills:
            continue
        for skill in skills:
            canonical = canonical_skill(skill)
            key = normalize_skill(canonical)
            if key and key not in seen:
                seen.add(key)
                result.append(canonical)
    return result


def as_skill_list(value: object) -> list[object]:
    """Accept the common list, scalar, and null shapes returned by extractors."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []


def extract_known_skills(text: str) -> list[str]:
    """Find known skills anywhere in text, including bullet and comma-separated sections."""
    if not text:
        return []
    normalized_text = normalize_skill(text)
    found: list[tuple[int, str]] = []
    for alias, canonical in sorted(KNOWN_SKILLS.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = r"(?<![\w+#])" + re.escape(alias) + r"(?![\w+#])"
        match = re.search(pattern, normalized_text)
        if match:
            found.append((match.start(), canonical))
    return merge_skills(canonical for _, canonical in sorted(found, key=lambda item: item[0]))
