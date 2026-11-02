
from app.workflow import job_workflow
from app.application_tracker import application_tracker


def show_menu():
    print("\n" + "=" * 45)
    print("          JOBAGENT - PERSONAL AI")
    print("=" * 45)
    print("1. Ask JobAgent a question")
    print("2. Search and analyze jobs")
    print("3. View saved jobs")
    print("4. Exit")
    print("=" * 45)


def ask_agent():
    instruction = input("\nWhat would you like to ask? ").strip()

    if not instruction:
        print("Please enter a question.")
        return

    try:
        response = job_workflow.run(instruction)

        print("\n=== JobAgent Response ===")
        print(response)

    except Exception as error:
        print(f"\nError: {error}")


def search_jobs():
    print("\nThis searches your configured roles and locations.")
    print("It may make multiple API requests and AI calls.")

    confirmation = input(
        "\nStart the real job search? (yes/no): "
    ).strip().lower()

    if confirmation not in ("yes", "y"):
        print("Job search cancelled.")
        return

    try:
        results = job_workflow.search_and_analyze_jobs(
            per_page=10
        )

        print("\n=== Job Search Results ===")

        for index, result in enumerate(
            results["analyses"], start=1
        ):
            job = result["job"]

            print("\n" + "-" * 45)
            print(f"Job {index}: {job.get('title', 'Unknown')}")
            print(f"Company: {job.get('company', 'Unknown')}")
            print(f"Location: {job.get('location', 'Unknown')}")
            print(f"Work mode: {job.get('work_mode', 'Unknown')}")
            print(f"URL: {job.get('job_url', 'Not available')}")

            if result.get("analysis"):
                print("\nAI Analysis:")
                print(result["analysis"])

            if result.get("error"):
                print("\nAnalysis error:", result["error"])

        print("\nNew jobs saved:", len(results["new_jobs"]))
        print("Duplicates skipped:", results["duplicates"])

    except Exception as error:
        print(f"\nJob search failed: {error}")


def view_saved_jobs():
    applications = application_tracker.get_all()

    print("\n=== Saved Jobs ===")

    if not applications:
        print("No jobs have been saved yet.")
        return

    for index, application in enumerate(applications, start=1):
        job = application.get("job", {})

        print("\n" + "-" * 45)
        print(f"Job {index}")
        print("Title:", job.get("title", "Unknown"))
        print("Company:", job.get("company", "Unknown"))
        print("Location:", job.get("location", "Unknown"))
        print("Status:", application.get("status", "Saved"))
        print("Job ID:", application.get("job_id", "Unknown"))
        print("URL:", job.get("job_url", "Not available"))

    update = input(
        "\nWould you like to update a job's status? (yes/no): "
    ).strip().lower()

    if update not in ("yes", "y"):
        return

    job_id = input("\nEnter the Job ID: ").strip()

    print("\nAvailable statuses:")
    print(", ".join(sorted(application_tracker.STATUSES)))

    status = input("\nEnter the new status: ").strip()

    try:
        application_tracker.update_status(job_id, status)
        print("\nJob status updated successfully!")

    except (ValueError, KeyError) as error:
        print(f"\nCould not update status: {error}")


def main():
    print("\nWelcome to JobAgent!")

    while True:
        show_menu()

        choice = input("\nChoose an option (1-4): ").strip()

        if choice == "1":
            ask_agent()

        elif choice == "2":
            search_jobs()

        elif choice == "3":
            view_saved_jobs()

        elif choice == "4":
            print("\nThanks for using JobAgent. Goodbye!")
            break

        else:
            print("\nInvalid choice. Please select 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
