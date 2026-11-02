
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.application_tracker import ApplicationTracker


def test_application_tracker():
    print("\n=== Application Tracker Test ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "applications.json"

        tracker = ApplicationTracker(file_path=test_file)

        sample_job = {
            "source": "Test Source",
            "source_id": "TEST001",
            "title": "Junior Python Developer",
            "company": "Example Company",
            "location": "Kochi",
            "job_url": "https://example.com/job",
        }

        # Test adding a job.
        result = tracker.add_job(sample_job)

        assert result["added"] is True
        print("Job saved successfully!")

        # Test duplicate detection.
        duplicate = tracker.add_job(sample_job)

        assert duplicate["added"] is False
        print("Duplicate job detected!")

        job_id = result["application"]["job_id"]

        # Test status updates.
        tracker.update_status(job_id, "Interested")

        assert tracker.get_job(job_id)["status"] == "Interested"
        print("Application status updated!")

        # Test notes.
        tracker.add_note(job_id, "Review this job before applying.")

        assert len(tracker.get_job(job_id)["notes"]) == 1
        print("Application note saved!")

        # Test persistence by loading the file again.
        tracker_again = ApplicationTracker(file_path=test_file)

        assert len(tracker_again.get_all()) == 1
        print("Application data persisted!")

        print("\nApplication Tracker test passed!")


if __name__ == "__main__":
    test_application_tracker()
