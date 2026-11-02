"""Offline unit tests for JobsForce India. No live API calls by default."""

import json
from pathlib import Path
import sys

import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.job_sources.jobsforce_india import JobsForceIndia


class FakeResponse:
    def __init__(self, data, status_code=200, headers=None):
        self._data = data
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def sample_api_job(job_id="1001", location=None, work_mode="On-site"):
    return {
        "id": job_id,
        "title": "Junior Python Developer",
        "employer": {"name": "Example Technologies"},
        "hiring": {"type": "direct"},
        "location": location or {"city": "Kochi", "state": "Kerala", "country": "India"},
        "work_mode": work_mode,
        "job_type": "Full-time",
        "salary": {"label": "₹20,000/month"},
        "experience": {"label": "Fresher"},
        "summary": "Python role",
        "url": "https://jobsforceindia.com/jobs/1001",
        "apply_url": "https://jobsforceindia.com/apply/1001",
    }


def test_search_jobs_normalizes_response_and_clamps_page_size():
    session = FakeSession([FakeResponse({"results": [sample_api_job()]})])
    source = JobsForceIndia(session=session, sleep=lambda _: None)
    jobs = source.search_jobs(keyword="Python", city="Kochi", per_page=99)

    assert len(jobs) == 1
    assert jobs[0]["source"] == "JobsForce India"
    assert jobs[0]["source_id"] == "1001"
    assert jobs[0]["company"] == "Example Technologies"
    assert jobs[0]["location"] == "Kochi"
    assert session.calls[0]["params"]["per_page"] == 20
    assert session.calls[0]["params"]["city"] == "Kochi"


def test_confidential_agency_employer_is_not_invented():
    job = sample_api_job()
    job["hiring"] = {"type": "agency"}
    job["employer"] = {"name": "Do not disclose"}
    source = JobsForceIndia(session=FakeSession([FakeResponse({"results": [job]})]))
    result = source.search_jobs()
    assert result[0]["company"] == "Confidential client (via JobsForce India)"


def test_remote_india_builds_remote_search_task():
    source = JobsForceIndia()
    tasks = source._build_tasks()
    remote_tasks = [t for t in tasks if t["location"] == "Remote India"]
    assert remote_tasks
    assert remote_tasks[0]["city"] is None
    assert remote_tasks[0]["work_mode"] == "Remote"


def test_search_progress_advances_only_after_success(tmp_path, monkeypatch):
    from app.job_sources import jobsforce_india as module
    from app.job_search import job_search

    monkeypatch.setattr(job_search, "search_roles", ["Python Developer"])
    monkeypatch.setattr(job_search, "search_locations", ["Kochi"])
    progress_file = tmp_path / "progress.json"

    # First query fails: next_index should remain at zero for retry.
    session = FakeSession([requests.Timeout("timeout")])
    source = JobsForceIndia(session=session, progress_file=progress_file, sleep=lambda _: None)
    # avoid repeated retries in this test
    source.REQUEST_RETRIES = 1
    results = source.search_all_preferences(max_searches=1)
    assert results == []
    saved = json.loads(progress_file.read_text(encoding="utf-8"))
    assert saved["next_index"] == 0

    # Then successful response advances it.
    source.session = FakeSession([FakeResponse({"results": [sample_api_job()]})])
    results = source.search_all_preferences(max_searches=1)
    assert len(results) == 1
    saved = json.loads(progress_file.read_text(encoding="utf-8"))
    assert saved["next_index"] == 1



def test_429_retry_after_is_respected():
    session = FakeSession([
        FakeResponse({}, status_code=429, headers={"Retry-After": "3"}),
        FakeResponse({"results": []}),
    ])
    waits = []
    source = JobsForceIndia(session=session, sleep=waits.append)
    assert source.search_jobs() == []
    assert waits == [3.0]


@pytest.mark.skipif(
    __import__("os").getenv("JOBAGENT_LIVE_API_TEST") != "1",
    reason="Set JOBAGENT_LIVE_API_TEST=1 to explicitly run a live API smoke test.",
)
def test_live_api_smoke_test():
    source = JobsForceIndia()
    results = source.search_jobs(keyword="Python developer fresher", city="Kochi", per_page=3)
    assert isinstance(results, list)
