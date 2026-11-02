"""Persistent application tracker with role-group and listing-level data."""

import json
import re
from datetime import datetime
from pathlib import Path

from app.config import PROJECT_ROOT


class ApplicationTracker:
    UNKNOWN_COMPANIES = {
        "unknown", "confidential", "confidential client",
        "confidential client via jobsforce india", "not disclosed",
        "undisclosed", "n a", "na",
    }

    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path is not None else (
            PROJECT_ROOT / "data" / "applications.json"
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.applications = self._load()
        changed = False
        for application in self.applications:
            if "analysis_group_id" not in application:
                application["analysis_group_id"] = self._get_analysis_group_id(
                    application.get("job", {}), application.get("job_id", "")
                )
                changed = True
            if "listing_assessment" not in application:
                application["listing_assessment"] = None
                changed = True
        if changed:
            self._save()

    def _load(self):
        if not self.file_path.exists():
            return []
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            print("Warning: Could not load applications.json; starting with an empty tracker.")
            return []

    def _save(self):
        """Atomic JSON write to reduce risk of corrupting tracker data."""
        temporary = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.applications, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self.file_path)

    @staticmethod
    def _canonical_url(url):
        url = str(url or "").strip().lower()
        if not url:
            return ""
        url = url.split("#", 1)[0]
        url = url.split("?", 1)[0]
        return url.rstrip("/")

    def _get_job_id(self, job):
        source = str(job.get("source") or "unknown").strip().lower()
        source_id = str(job.get("source_id") or "").strip()
        if source_id:
            return f"{source}:{source_id}"

        url = self._canonical_url(job.get("job_url") or job.get("apply_url") or job.get("url"))
        if url:
            return f"{source}:{url}"

        title = self._normalize_text(job.get("title") or "unknown")
        company = self._normalize_text(job.get("company") or "unknown")
        location = self._normalize_text(job.get("location") or "unknown")
        return f"{source}:{title}|{company}|{location}"

    @staticmethod
    def _normalize_text(value):
        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    def _get_analysis_group_id(self, job, job_id):
        company = self._normalize_text(job.get("company", ""))
        title = self._normalize_text(job.get("title", ""))
        if not company or company in self.UNKNOWN_COMPANIES or not title:
            return f"listing:{job_id}"
        return f"company-role:{company}|{title}"

    def _get_group_applications(self, group_id):
        return [a for a in self.applications if a.get("analysis_group_id") == group_id]

    def get_group_applications(self, job_id):
        application = self.get_job(job_id)
        if not application:
            return []
        return self._get_group_applications(application.get("analysis_group_id", job_id))

    def add_job(self, job):
        job_id = self._get_job_id(job)
        existing = self.get_job(job_id)
        if existing:
            return {"added": False, "reason": "Duplicate job", "application": existing}

        group_id = self._get_analysis_group_id(job, job_id)
        group_apps = self._get_group_applications(group_id)
        shared_analysis = next((
            item.get("analysis") for item in group_apps
            if item.get("analysis_status") == "Completed" and item.get("analysis") is not None
        ), None)
        now = datetime.now().isoformat()
        application = {
            "job_id": job_id,
            "job": job,
            "analysis_group_id": group_id,
            "status": "Discovered",
            "discovered_at": now,
            "updated_at": now,
            "applied_at": None,
            "notes": [],
            "analysis_status": "Completed" if shared_analysis is not None else "Pending",
            "analysis": shared_analysis,
            "analysis_error": None,
            "listing_assessment": None,
        }
        self.applications.append(application)
        self._save()
        return {"added": True, "reason": "New job saved", "application": application}

    def get_pending_analysis(self, limit=5):
        pending = []
        seen_groups = set()
        for application in self.applications:
            group_id = application.get("analysis_group_id", application.get("job_id"))
            if group_id in seen_groups:
                continue
            seen_groups.add(group_id)
            group_apps = self._get_group_applications(group_id)
            if any(a.get("analysis_status") == "Completed" and a.get("analysis") is not None for a in group_apps):
                continue
            if any(a.get("analysis_status") in {"Pending", "Failed"} for a in group_apps):
                pending.append(application)
        return pending if limit is None else pending[:max(0, int(limit))]

    def save_analysis(self, job_id, analysis):
        application = self.get_job(job_id)
        if not application:
            return False
        group_id = application.get("analysis_group_id", job_id)
        now = datetime.now().isoformat()
        for item in self._get_group_applications(group_id):
            item["analysis"] = analysis
            item["analysis_status"] = "Completed"
            item["analysis_error"] = None
            item["updated_at"] = now
        self._save()
        return True

    def save_listing_assessment(self, job_id, listing_assessment):
        application = self.get_job(job_id)
        if not application:
            return False
        application["listing_assessment"] = listing_assessment
        application["updated_at"] = datetime.now().isoformat()
        self._save()
        return True

    def mark_analysis_failed(self, job_id, error):
        application = self.get_job(job_id)
        if not application:
            return False
        group_id = application.get("analysis_group_id", job_id)
        now = datetime.now().isoformat()
        for item in self._get_group_applications(group_id):
            item["analysis_status"] = "Failed"
            item["analysis_error"] = str(error)
            item["updated_at"] = now
        self._save()
        return True

    def update_status(self, job_id, status):
        application = self.get_job(job_id)
        if not application:
            return False
        now = datetime.now().isoformat()
        application["status"] = status
        application["updated_at"] = now
        if status == "Applied":
            application["applied_at"] = now
        self._save()
        return True

    def add_note(self, job_id, note):
        application = self.get_job(job_id)
        if not application:
            return False
        application.setdefault("notes", []).append({
            "note": note,
            "created_at": datetime.now().isoformat(),
        })
        application["updated_at"] = datetime.now().isoformat()
        self._save()
        return True

    def get_all(self):
        return self.applications

    def get_job(self, job_id):
        return next((a for a in self.applications if a.get("job_id") == job_id), None)

    def get_summary(self):
        status_counts = {}
        for application in self.applications:
            status = application.get("status", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        groups = {}
        for application in self.applications:
            groups.setdefault(application.get("analysis_group_id", application.get("job_id")), application)

        completed = sum(
            1 for group_id in groups
            if any(a.get("analysis_status") == "Completed" and a.get("analysis") is not None
                   for a in self._get_group_applications(group_id))
        )
        pending = sum(
            1 for group_id in groups
            if any(a.get("analysis_status") in {"Pending", "Failed"}
                   for a in self._get_group_applications(group_id))
            and not any(a.get("analysis_status") == "Completed" and a.get("analysis") is not None
                        for a in self._get_group_applications(group_id))
        )
        return {
            "total_applications": len(self.applications),
            "status_counts": status_counts,
            "unique_analysis_groups": len(groups),
            "completed_analysis_groups": completed,
            "pending_analysis_groups": pending,
        }


application_tracker = ApplicationTracker()
