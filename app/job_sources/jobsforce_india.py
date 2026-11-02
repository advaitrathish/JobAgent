"""JobsForce India public read-only API integration.

API docs: https://jobsforceindia.com/developers
Endpoint: GET https://jobsforceindia.com/api/public/v1/jobs
No API key is required. Keep requests below the documented rate limit.
"""

import json
import time
from pathlib import Path
from datetime import datetime

import requests

from app.job_search import job_search


class JobsForceIndia:
    API_URL = "https://jobsforceindia.com/api/public/v1/jobs"
    SOURCE_NAME = "JobsForce India"
    MAX_PER_PAGE = 20
    DEFAULT_MAX_SEARCHES = 12
    REQUEST_RETRIES = 3
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    # City preference -> API city filter spelling.
    CITY_ALIASES = {
        "hydra bad": "Hyderabad",
        "hydrabad": "Hyderabad",
        "trivandrum": "Thiruvananthapuram",
        "thiruvananthapuram": "Thiruvananthapuram",
    }

    def __init__(self, timeout=30, progress_file=None, session=None, sleep=time.sleep):
        self.timeout = timeout
        self.session = session or requests
        self.sleep = sleep
        self.last_errors = []
        self.last_run = {}
        self.progress_file = Path(progress_file) if progress_file else (
            Path(__file__).resolve().parents[2] / "data" / "job_search_progress.json"
        )

    @staticmethod
    def _safe_dict(value):
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _safe_text(value):
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value).strip()

    @classmethod
    def _extract_location(cls, value):
        if isinstance(value, dict):
            city = cls._safe_text(value.get("city"))
            state = cls._safe_text(value.get("state"))
            country = cls._safe_text(value.get("country"))
            return city, state, country
        text = cls._safe_text(value)
        return text, "", ""

    def _request(self, params):
        """Request with bounded retry and Retry-After support for 429."""
        last_exception = None

        for attempt in range(self.REQUEST_RETRIES):
            try:
                response = self.session.get(
                    self.API_URL,
                    params=params,
                    timeout=self.timeout,
                )

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    if attempt == self.REQUEST_RETRIES - 1:
                        response.raise_for_status()

                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        delay = min(max(float(retry_after), 1.0), 60.0)
                    except (TypeError, ValueError):
                        delay = min(2 ** attempt, 10)

                    self.sleep(delay)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as exc:
                last_exception = exc
                if attempt == self.REQUEST_RETRIES - 1:
                    break
                self.sleep(min(2 ** attempt, 10))

        raise RuntimeError(f"JobsForce India API request failed: {last_exception}") from last_exception

    def search_jobs(
        self,
        keyword="Python developer",
        city=None,
        work_mode=None,
        fresher=True,
        per_page=10,
        page=1,
        **filters,
    ):
        """Search API. Only documented parameters are sent."""
        per_page = min(max(int(per_page), 1), self.MAX_PER_PAGE)
        page = min(max(int(page), 1), 10)

        params = {
            "q": str(keyword).strip(),
            "fresher": str(bool(fresher)).lower(),
            "per_page": per_page,
            "page": page,
        }

        if city:
            city_key = str(city).strip().lower()
            params["city"] = self.CITY_ALIASES.get(city_key, city)
        if work_mode:
            params["work_mode"] = work_mode

        allowed_filters = {
            "category", "job_type", "experience_years", "min_monthly_pay",
            "posted_within_days",
        }
        for key, value in filters.items():
            if key in allowed_filters and value is not None and value != "":
                params[key] = value

        try:
            response = self._request(params)
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"JobsForce India API request failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"JobsForce India returned invalid JSON: {exc}") from exc

        # API documentation describes an object with a `results` array.
        if isinstance(data, list):
            results = data  # tolerant fallback for a future API response shape
        elif isinstance(data, dict):
            results = data.get("results", data.get("jobs", []))
        else:
            raise RuntimeError("Unexpected JobsForce India response format.")

        if not isinstance(results, list):
            raise RuntimeError("JobsForce India response has no jobs list.")

        normalized = []
        for item in results:
            if not isinstance(item, dict):
                continue

            location_obj = self._safe_dict(item.get("location"))
            salary_obj = self._safe_dict(item.get("salary"))
            experience_obj = self._safe_dict(item.get("experience"))
            employer_obj = self._safe_dict(item.get("employer"))
            hiring_obj = self._safe_dict(item.get("hiring"))

            city_text, state_text, country_text = self._extract_location(
                item.get("location")
            )
            hiring_type = self._safe_text(hiring_obj.get("type"))

            if hiring_type.lower() == "agency":
                company = "Confidential client (via JobsForce India)"
            else:
                company = self._safe_text(
                    employer_obj.get("name") or item.get("company")
                )

            job_id = item.get("id")
            job_url = self._safe_text(item.get("url") or item.get("job_url"))
            apply_url = self._safe_text(item.get("apply_url"))

            normalized.append({
                "source": self.SOURCE_NAME,
                "source_id": self._safe_text(job_id),
                "title": self._safe_text(item.get("title")),
                "company": company,
                "hiring_type": hiring_type,
                "location": city_text,
                "state": state_text,
                "country": country_text,
                "work_mode": self._safe_text(item.get("work_mode")),
                "job_type": self._safe_text(item.get("job_type")),
                "salary": self._safe_text(salary_obj.get("label") or item.get("salary_label")),
                "experience": self._safe_text(experience_obj.get("label") or item.get("experience_label")),
                "summary": self._safe_text(item.get("summary") or item.get("description")),
                "job_url": job_url,
                "apply_url": apply_url,
                "posted_at": self._safe_text(item.get("posted_at") or item.get("created_at")),
                "remote_eligibility": self._safe_text(
                    item.get("remote_eligibility") or item.get("eligible_countries")
                ),
            })

        return normalized

    def _build_tasks(self):
        preferences = job_search.get_search_preferences()
        roles = preferences.get("roles", [])
        locations = preferences.get("locations", [])

        tasks = []
        for role in roles:
            for location in locations:
                normalized_location = str(location).strip().lower()
                if normalized_location == "remote india":
                    tasks.append({
                        "role": role,
                        "location": "Remote India",
                        "city": None,
                        "work_mode": "Remote",
                        "query": role,
                    })
                elif normalized_location == "kerala":
                    # API `city` expects a city; use state as a keyword instead.
                    tasks.append({
                        "role": role,
                        "location": location,
                        "city": None,
                        "work_mode": None,
                        "query": f"{role} Kerala",
                    })
                else:
                    tasks.append({
                        "role": role,
                        "location": location,
                        "city": location,
                        "work_mode": None,
                        "query": role,
                    })
        return tasks

    @staticmethod
    def _task_signature(tasks):
        canonical = json.dumps(tasks, sort_keys=True, ensure_ascii=False)
        # Hash not necessary; storing the canonical string is transparent/debuggable.
        return canonical

    def _load_progress(self, task_signature=None):
        if not self.progress_file.exists():
            return {"next_index": 0, "task_signature": task_signature}

        try:
            data = json.loads(self.progress_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("progress file root must be an object")

            # Backward compatibility with the earlier {"next_index": 12} format.
            saved_signature = data.get("task_signature")
            if task_signature and not saved_signature:
                # Legacy progress stored only an index. The task ordering/normalization
                # has changed, so we cannot prove that this index still maps correctly.
                # Restart safely; the tracker will deduplicate already-saved listings.
                print("Legacy search progress detected; restarting at query 1 to avoid skipping preferences.")
                return {"next_index": 0, "task_signature": task_signature}
            if task_signature and saved_signature != task_signature:
                print("Search preferences changed; resetting JobsForce India progress to query 1.")
                return {"next_index": 0, "task_signature": task_signature}

            index = max(0, int(data.get("next_index", 0)))
            return {
                "next_index": index,
                "task_signature": task_signature or saved_signature,
            }
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            print("Warning: progress file is invalid; restarting this search cycle.")
            return {"next_index": 0, "task_signature": task_signature}

    def _save_progress(self, next_index, task_signature, last_completed=None):
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "next_index": int(next_index),
            "task_signature": task_signature,
            "last_completed": last_completed,
            "updated_at": datetime.now().isoformat(),
        }
        temporary_file = self.progress_file.with_suffix(self.progress_file.suffix + ".tmp")
        temporary_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary_file.replace(self.progress_file)

    @staticmethod
    def _get_unique_job_id(job):
        source_id = str(job.get("source_id") or "").strip()
        source = str(job.get("source") or JobsForceIndia.SOURCE_NAME).strip().lower()
        if source_id:
            return f"{source}:{source_id}"

        for key in ("job_url", "apply_url"):
            url = str(job.get(key) or "").strip()
            if url:
                return url.split("#", 1)[0].rstrip("/").lower()

        return (
            str(job.get("title") or "").strip().lower(),
            str(job.get("company") or "").strip().lower(),
            str(job.get("location") or "").strip().lower(),
        )

    def search_all_preferences(self, per_page=10, max_searches=DEFAULT_MAX_SEARCHES):
        """Run a resumable batch of searches; failed query remains next to retry."""
        tasks = self._build_tasks()
        self.last_errors = []
        self.last_run = {"total_queries": len(tasks), "attempted": 0, "failed": 0}

        if not tasks:
            print("No job-search preferences configured.")
            return []

        signature = self._task_signature(tasks)
        progress = self._load_progress(signature)
        start_index = progress["next_index"]

        if start_index >= len(tasks):
            print("JobsForce India search cycle completed; starting a fresh cycle.")
            start_index = 0
            self._save_progress(0, signature)

        max_searches = max(1, int(max_searches))
        end_index = min(start_index + max_searches, len(tasks))
        all_jobs = []
        seen = set()

        print("\n=== JobsForce India Search ===")
        print(f"Queries configured: {len(tasks)} | this batch: {end_index - start_index}")
        print(f"Resume position: {start_index + 1}/{len(tasks)}")

        for index in range(start_index, end_index):
            task = tasks[index]
            location_label = task["location"]
            print(f"\n[{index + 1}/{len(tasks)}] {task['role']} — {location_label}")

            try:
                results = self.search_jobs(
                    keyword=task["query"],
                    city=task["city"],
                    work_mode=task["work_mode"],
                    fresher=True,
                    per_page=per_page,
                )
            except (RuntimeError, KeyboardInterrupt) as exc:
                if isinstance(exc, KeyboardInterrupt):
                    print("Search interrupted. Progress remains on this query for retry.")
                    break
                self.last_errors.append({
                    "query_index": index,
                    "task": task,
                    "error": str(exc),
                })
                self.last_run["failed"] += 1
                print(f"Request failed; this query will retry next run: {exc}")
                # Persist the current index so the retry position is explicit.
                # Important: don't advance the index on failure.
                self._save_progress(index, signature)
                break

            for job in results:
                key = self._get_unique_job_id(job)
                if key not in seen:
                    seen.add(key)
                    all_jobs.append(job)

            self.last_run["attempted"] += 1
            print(f"Listings returned: {len(results)} | unique in this batch: {len(all_jobs)}")
            self._save_progress(index + 1, signature, last_completed=task)

            # Stay well under the published 120 requests/minute limit.
            if index + 1 < end_index:
                self.sleep(0.5)

        next_index = self._load_progress(signature)["next_index"]
        if next_index >= len(tasks):
            print("All configured JobsForce India queries completed this cycle.")
        else:
            print(f"Progress saved. Next query: {next_index + 1}/{len(tasks)}")

        print(f"Collected unique listings this batch: {len(all_jobs)}")
        if self.last_errors:
            print(f"Failed requests: {len(self.last_errors)} (not skipped; retry next run)")
        return all_jobs


jobsforce_india = JobsForceIndia()
