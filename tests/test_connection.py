"""Manual FreeLLMAPI connection smoke test. Run explicitly with python."""

import os
from openai import OpenAI
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()
    client = OpenAI(
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
    )
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "auto"),
        messages=[{"role": "user", "content": "Reply with: JobAgent connection successful!"}],
    )
    print(response.choices[0].message.content)
