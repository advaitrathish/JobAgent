"""Manual AI client smoke test. Run explicitly with: python tests/test_ai_client.py"""

from app.ai_client import ai_client


if __name__ == "__main__":
    print("Testing JobAgent AI client...")
    response = ai_client.generate(
        prompt="Reply with exactly: JobAgent AI client is working!"
    )
    print("\nAI Response:")
    print(response)
