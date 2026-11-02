import sys
from pathlib import Path

# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.job_analyzer import JobAnalyzer


class FakeAI:
    """Simulate an AI response without making an API request."""

    def generate(self, prompt, system_prompt=None, **kwargs):
        return """
        {
            "job_title": "Junior Python Developer",
            "company": "Example Company",
            "suitability_score": 85,
            "recommendation": "Apply",
            "experience_eligibility": "Suitable for fresher",
            "skills_match": ["Python"],
            "missing_skills": ["Django"],
            "location_match": "Suitable",
            "remote_eligibility": "Unknown",
            "reasons": ["Python matches the user's skills"],
            "concerns": ["Django experience is not confirmed"],
            "summary": "Potentially suitable entry-level opportunity"
        }
        """


def test_job_analyzer():
    """Test job analysis using simulated AI."""

    print("\n=== Job Analyzer Test ===")

    analyzer = JobAnalyzer(ai=FakeAI())

    sample_job = {
        "source": "Test Source",
        "source_id": "TEST001",
        "title": "Junior Python Developer",
        "company": "Example Company",
        "location": "Kochi",
        "work_mode": "Remote",
        "job_type": "Full-time",
        "salary": "Not provided",
        "experience": "Fresher",
        "summary": "Looking for a junior Python developer.",
        "job_url": "https://example.com/job",
        "apply_url": "https://example.com/apply",
    }

    result = analyzer.analyze_job(sample_job)

    print("\nJob title:", result["job"]["title"])
    print("\nAI analysis:")
    print(result["analysis"])

    assert result["job"]["title"] == "Junior Python Developer"
    assert "suitability_score" in result["analysis"]
    assert "recommendation" in result["analysis"]

    print("\nJob Analyzer test passed!")


class FakeJobSource:
    """Simulate job search without API requests."""

    def search_all_preferences(self, per_page=10):
        return [
            {
                "source": "Test Source",
                "source_id": "TEST001",
                "title": "Junior Python Developer",
                "company": "Example Company",
                "location": "Kochi",
                "work_mode": "Remote",
                "job_url": "https://example.com/job",
            }
        ]


class FakeTracker:
    """Simulate tracking without modifying real files."""

    def __init__(self):
        self.saved_jobs = {}

    def add_job(self, job):
        """Save a job unless it already exists."""

        job_id = job.get("source_id")

        if job_id in self.saved_jobs:
            return {
                "added": False,
                "reason": "Duplicate job",
                "application": self.saved_jobs[job_id],
            }

        application = {
            "job_id": job_id,
            "job": job,
            "analysis_status": "Pending",
            "analysis": None,
        }

        self.saved_jobs[job_id] = application

        return {
            "added": True,
            "reason": "New job saved",
            "application": application,
        }

    def get_pending_analysis(self, limit=None):
        """Return jobs awaiting analysis."""

        pending = [
            application
            for application in self.saved_jobs.values()
            if application.get("analysis_status", "Pending")
            in {"Pending", "Failed"}
        ]

        if limit is not None:
            pending = pending[:limit]

        return pending

    def save_analysis(self, job_id, analysis):
        """Save a completed analysis."""

        application = self.saved_jobs[job_id]

        application["analysis"] = analysis
        application["analysis_status"] = "Completed"

        return application

    def mark_analysis_failed(self, job_id, error):
        """Record an analysis failure."""

        application = self.saved_jobs[job_id]

        application["analysis_status"] = "Failed"
        application["analysis_error"] = str(error)

        return application


def test_search_and_analyze_workflow():
    """Test searching, saving, analyzing, and duplicate detection."""

    print("\n=== Job Workflow Integration Test ===")

    from app.workflow import JobWorkflow

    workflow = JobWorkflow(
        job_source=FakeJobSource(),
        analyzer=JobAnalyzer(ai=FakeAI()),
        tracker=FakeTracker(),
    )

    # First search: save and analyze the new job.
    result = workflow.search_and_analyze_jobs()

    assert len(result["jobs"]) == 1
    assert len(result["new_jobs"]) == 1
    assert len(result["analyses"]) == 1
    assert result["duplicates"] == 0
    assert result["completed"] == 1

    print("\nFirst search: new job saved and analyzed!")

    # Second search: the same job should be recognized as a duplicate.
    result = workflow.search_and_analyze_jobs()

    assert len(result["new_jobs"]) == 0
    assert len(result["analyses"]) == 0
    assert result["duplicates"] == 1
    assert result["completed"] == 0

    print("\nSecond search: duplicate correctly skipped!")
    print("\nWorkflow integration test passed!")


if __name__ == "__main__":
    test_job_analyzer()
    test_search_and_analyze_workflow()
