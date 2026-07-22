from app.llm.groq_client import GroqClient

RESUME_EXTRACTION_SYSTEM_PROMPT = """You are a resume parsing engine. Given raw resume text, extract structured information and return ONLY a valid JSON object with this exact structure:

{
  "full_name": string or null,
  "current_designation": string or null,
  "total_experience_years": number or null,
  "skills": [string],
  "education": [
    {"degree": string, "institution": string or null, "year": string or null}
  ],
  "work_experience": [
    {"company": string, "designation": string or null, "duration": string or null}
  ],
  "certifications": [string],
  "summary": string or null
}

Rules:
- If information is not present in the resume, use null or an empty list — never fabricate data.
- skills should be a flat list of distinct technical and professional skills, deduplicated.
- Do not include any text outside the JSON object."""


class ResumeExtractor:
    def __init__(self):
        self.groq = GroqClient()

    def extract(self, cleaned_text: str) -> dict:
        
        truncated = cleaned_text[:12000]
        return self.groq.extract_json(
            system_prompt=RESUME_EXTRACTION_SYSTEM_PROMPT,
            user_content=truncated,
        )