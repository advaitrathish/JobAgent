
import time

from openai import OpenAI

from app import config


class AIClient:
    """Reusable AI client for JobAgent."""

    def __init__(self):
        if not config.LLM_BASE_URL:
            raise ValueError("LLM_BASE_URL is missing from .env")

        if not config.LLM_API_KEY:
            raise ValueError("LLM_API_KEY is missing from .env")

        self.client = OpenAI(
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY,
            timeout=60.0,
            max_retries=2,
        )

        self.model = config.LLM_MODEL

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are JobAgent, an intelligent job-search assistant.",
        max_tokens: int = 1500,
        temperature: float = 0.3,
    ) -> str:
        """Generate a response from the configured AI model."""

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                result = response.choices[0].message.content

                if not result:
                    raise RuntimeError("The AI returned an empty response.")

                return result.strip()

            except Exception as error:
                if attempt == 0:
                    time.sleep(2)
                else:
                    raise RuntimeError(
                        f"JobAgent AI request failed: {error}"
                    ) from error


# Create a reusable AI client
ai_client = AIClient()
