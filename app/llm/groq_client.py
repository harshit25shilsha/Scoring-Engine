import json

from groq import Groq

from app.config import settings
from app.config.logging import logger

GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def extract_json(self, system_prompt: str, user_content: str) -> dict:
        
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"[groq] invalid JSON returned: {e} | raw={raw[:300]}")
            raise ValueError("Groq did not return valid JSON") from e