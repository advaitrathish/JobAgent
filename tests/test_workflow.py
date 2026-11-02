"""Manual conversational JobAgent test. Run explicitly with python."""

from app.workflow import job_workflow


if __name__ == "__main__":
    print("Testing JobAgent workflow...")
    response = job_workflow.run(
        "Explain how you will help me find suitable entry-level Python and AI jobs."
    )
    print("\nWorkflow response:")
    print(response)
    print("\nWorkflow test completed!")
