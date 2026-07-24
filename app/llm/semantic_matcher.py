from app.llm.groq_client import GroqClient

SEMANTIC_MATCH_SYSTEM_PROMPT = """You are an expert technical recruiter. Compare a candidate's structured resume data against a job's structured requirements, and return ONLY a valid JSON object with this exact structure:

{
  "semantic_score": number (0-100),
  "strengths": [string],
  "weaknesses": [string],
  "missing_skills": [string],
  "recommendation": string
}

Rules:
- semantic_score reflects overall fit based on meaning and context, not just keyword overlap — consider related/transferable skills, seniority alignment, and domain relevance.
- strengths: 2-4 specific reasons this candidate fits well.
- weaknesses: 2-4 specific gaps or concerns, phrased constructively.
- missing_skills: skills genuinely absent or not evidenced, even if conceptually related skills exist.
- recommendation: one or two sentences, direct and actionable (e.g., "Strong fit, recommend for interview" or "Significant experience gap, consider only if other candidates are unavailable").
- Do not include any text outside the JSON object."""


class SemanticMatcher:
    def __init__(self):
        self.groq = GroqClient()

    def compare(self, candidate_structured: dict, job_structured: dict) -> dict:
        user_content = (
            f"CANDIDATE PROFILE:\n{candidate_structured}\n\n"
            f"JOB REQUIREMENTS:\n{job_structured}"
        )
        return self.groq.extract_json(
            system_prompt=SEMANTIC_MATCH_SYSTEM_PROMPT,
            user_content=user_content,
        )