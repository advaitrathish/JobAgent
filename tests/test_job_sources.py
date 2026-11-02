"""Manual job source registry check. Run explicitly with python."""

from app.job_search import job_search


if __name__ == "__main__":
    print("\n=== JobAgent Job Sources Test ===")
    sources = job_search.get_job_sources()
    print(f"\nTotal enabled job sources: {len(sources)}")
    for source_id, source in sources.items():
        print(f"- {source['name']} ({source_id})")
    print("\nJob sources test completed!")
