"""Manual JobAgent smoke test. Run with: python tests/test_agent.py"""

from app.agent import job_agent


if __name__ == "__main__":
    print("Testing JobAgent...")
    response = job_agent.respond(
        "Briefly summarize my programming skills and preferred job locations."
    )
    print("\nJobAgent response:")
    print(response)
    print("\nAgent test completed!")
