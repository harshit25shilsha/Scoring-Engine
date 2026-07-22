from app.llm.groq_client import GroqClient

JD_EXTRACTION_SYSTEM_PROMPT = """You are a job description parsing engine. Given a raw job description, extract structured requirements and return ONLY a valid JSON object with this exact structure:

{
  "job_title": string or null,
  "required_skills": [string],
  "preferred_skills": [string],
  "minimum_experience_years": number or null,
  "maximum_experience_years": number or null,
  "education_requirements": [string],
  "responsibilities": [string],
  "employment_type": string or null,
  "summary": string or null
}

Rules:
- required_skills = must-have skills explicitly stated as required/mandatory.
- preferred_skills = "nice to have", "bonus", or "preferred" skills — keep separate from required_skills.
- If information is not present in the text, use null or an empty list — never fabricate data.
- Do not include any text outside the JSON object."""


class JDExtractor:
    def __init__(self):
        self.groq = GroqClient()

    def extract(self, cleaned_jd: str) -> dict:
        truncated = cleaned_jd[:12000]
        return self.groq.extract_json(
            system_prompt=JD_EXTRACTION_SYSTEM_PROMPT,
            user_content=truncated,
        )