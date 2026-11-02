
import json
from datetime import datetime
from pathlib import Path


class JobSearch:
    """Search preferences and source registry for JobAgent."""

    PROFILE_FILE = (
        Path(__file__).resolve().parents[1] / "data" / "profile.json"
    )

    DEFAULT_LOCATIONS = [
        "Palakkad",
        "Thrissur",
        "Kochi",
        "Thiruvananthapuram",
        "Kozhikode",
        "Bengaluru",
        "Chennai",
        "Hyderabad",
        "Mumbai",
        "Pune",
        "Coimbatore",
        "Mysuru",
        "Mangalore",
        "Delhi NCR",
        "Gurugram",
        "Noida",
        "Remote India",
        "Global Remote",
    ]

    DEFAULT_ROLES = [
        "Python Developer",
        "Junior Python Developer",
        "Backend Python Developer",
        "Full Stack Developer",
        "Junior Full Stack Developer",
        "AI Developer",
        "AI Engineer",
        "Generative AI Developer",
        "Machine Learning Intern",
        "Python Developer Intern",
        "Backend Developer Intern",
        "Software Developer",
        "Software Development Intern",
    ]

    JOB_SOURCES = {
        "jobsforce_india": {
            "name": "JobsForce India",
            "type": "api",
            "enabled": True,
        },
        "jobvetta": {
            "name": "Jobvetta",
            "type": "api",
            "enabled": True,
        },
        "linkedin": {
            "name": "LinkedIn",
            "type": "official_or_permitted_access",
            "enabled": True,
        },
        "indeed": {
            "name": "Indeed",
            "type": "official_or_permitted_access",
            "enabled": True,
        },
        "glassdoor": {
            "name": "Glassdoor",
            "type": "company_research",
            "enabled": True,
        },
        "upwork": {
            "name": "Upwork",
            "type": "official_or_permitted_access",
            "enabled": True,
        },
        "naukri": {
            "name": "Naukri",
            "type": "official_or_permitted_access",
            "enabled": True,
        },
        "apna": {
            "name": "Apna",
            "type": "official_or_permitted_access",
            "enabled": True,
        },
        "shine": {
            "name": "Shine",
            "type": "official_or_permitted_access",
            "enabled": True,
        },
        "hirist": {
            "name": "Hirist",
            "type": "official_or_permitted_access",
            "enabled": True,
        },
        "internshala": {
            "name": "Internshala",
            "type": "official_or_permitted_access",
            "enabled": True,
        },
    }

    def __init__(self, profile_file=None):
        self.profile_file = (
            Path(profile_file) if profile_file else self.PROFILE_FILE
        )

        self.search_locations = list(self.DEFAULT_LOCATIONS)
        self.search_roles = list(self.DEFAULT_ROLES)

        self._load_profile_preferences()

    def _load_profile_preferences(self):
        """Load search preferences from profile.json."""

        if not self.profile_file.exists():
            print("Profile not found. Using default search preferences.")
            return

        try:
            with self.profile_file.open("r", encoding="utf-8") as file:
                profile = json.load(file)

            personal = profile.get("personal", {})
            job_preferences = profile.get("job_preferences", {})

            locations = personal.get("preferred_locations")
            roles = job_preferences.get("roles")

            if isinstance(locations, list) and locations:
                self.search_locations = self._clean_preferences(locations)

            if isinstance(roles, list) and roles:
                self.search_roles = self._clean_preferences(roles)

            print(
                f"Loaded profile preferences: "
                f"{len(self.search_roles)} roles, "
                f"{len(self.search_locations)} locations."
            )

        except (json.JSONDecodeError, OSError, TypeError) as exc:
            print(
                f"Warning: Could not load profile preferences: {exc}. "
                "Using defaults."
            )

    @staticmethod
    def _clean_preferences(values):
        """Remove empty values and duplicate preferences."""

        cleaned = []
        seen = set()

        for value in values:
            if not isinstance(value, str):
                continue

            value = value.strip()

            if not value:
                continue

            normalized = value.casefold()

            if normalized not in seen:
                seen.add(normalized)
                cleaned.append(value)

        return cleaned

    def reload_preferences(self):
        """Reload preferences after profile.json changes."""

        self.search_locations = list(self.DEFAULT_LOCATIONS)
        self.search_roles = list(self.DEFAULT_ROLES)

        self._load_profile_preferences()

    def get_search_preferences(self):
        return {
            "locations": list(self.search_locations),
            "roles": list(self.search_roles),
            "experience": "Entry-level, fresher, graduate, internship",
            "last_updated": datetime.now().isoformat(),
        }

    def build_search_queries(self):
        return [
            {
                "role": role,
                "location": location,
                "query": f"{role} in {location}",
            }
            for role in self.search_roles
            for location in self.search_locations
        ]

    def get_job_sources(self):
        return {
            source_id: source
            for source_id, source in self.JOB_SOURCES.items()
            if source["enabled"]
        }


job_search = JobSearch()
