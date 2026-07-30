import json
import time
from groq import Groq, RateLimitError

from app.config import settings
from app.config.logging import logger

GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def extract_json(self, system_prompt: str, user_content: str, max_retries: int = 3) -> dict:
        last_error = None
        
        for attempt in range(1, max_retries+1):
            try:
                
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
            
            except RateLimitError as e:
                last_error = e
                wait_seconds = attempt * 15 
                logger.warning(
                    f"[groq] rate limit hit (attempt{attempt}/{max_retries}),"
                    f"waiting {wait_seconds}s before retry"
                )
                
                time.sleep(wait_seconds)
        
        logger.error(f"[groq] exhausted {max_retries} retries due to rate limiting")
        raise last_error

                