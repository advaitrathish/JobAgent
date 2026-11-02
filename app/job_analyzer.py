
"""AI-based job fit analysis plus deterministic listing/location assessment."""

import json
import re
from pathlib import Path

from app.ai_client import ai_client
from app.knowledge_base import knowledge_base
from app.memory import agent_memory
from app.job_search import job_search


class JobAnalyzer:
    LOCATION_FIELDS = {
        "location_match",
        "remote_eligibility",
        "remote_match",
        "location_status",
        "matched_locations",
        "matched_preferences",
        "is_remote",
        "job_location",
        "work_mode",
    }

    def __init__(self, ai=None, knowledge=None, memory=None):
        self.ai = ai or ai_client
        self.knowledge = knowledge or knowledge_base
        self.memory = memory or agent_memory

        self.profile_file = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "profile.json"
        )

    @staticmethod
    def _extract_job(job):
        if isinstance(job, dict) and isinstance(job.get("job"), dict):
            return job["job"]
        return job

    def _load_profile_from_file(self):
        """Load the candidate profile directly from data/profile.json."""

        if not self.profile_file.exists():
            return {}

        try:
            with self.profile_file.open("r", encoding="utf-8") as file:
                profile = json.load(file)

            if isinstance(profile, dict):
                return profile

            return {}

        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: Could not load profile.json: {exc}")
            return {}

    def get_profile_context(self):
        """Prefer the actual profile file, then fall back to knowledge base."""

        profile = self._load_profile_from_file()

        if not profile:
            profile = self.knowledge.get_information("profile", {})

        if not isinstance(profile, dict):
            profile = {}

        lessons = self.memory.get_lessons()

        return {
            "profile": profile,
            "previous_learning": lessons,
        }

    def _parse_json_response(self, response):
        """Parse and validate the AI's JSON response."""

        if not isinstance(response, str):
            raise ValueError("AI response must be a string.")

        response = response.strip()

        # Remove Markdown code fences if the model adds them.
        response = re.sub(
            r"^```(?:json)?\s*",
            "",
            response,
            flags=re.IGNORECASE,
        )

        response = re.sub(r"\s*```$", "", response)

        try:
            data = json.loads(response)

        except json.JSONDecodeError as exc:
            # Try extracting a JSON object if the model added extra text.
            start = response.find("{")
            end = response.rfind("}")

            if start == -1 or end <= start:
                raise ValueError(
                    f"AI returned invalid JSON: {exc}"
                ) from exc

            try:
                data = json.loads(response[start:end + 1])

            except json.JSONDecodeError as inner_exc:
                raise ValueError(
                    f"AI returned invalid JSON: {inner_exc}"
                ) from inner_exc

        if not isinstance(data, dict):
            raise ValueError("AI response must contain a JSON object.")

        required = (
            "job_title",
            "company",
            "suitability_score",
            "recommendation",
            "summary",
        )

        for field in required:
            if field not in data:
                raise ValueError(
                    f"AI response missing required field: {field}"
                )

        try:
            score = int(data["suitability_score"])

        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Suitability score must be a number."
            ) from exc

        if not 0 <= score <= 100:
            raise ValueError(
                "Suitability score must be between 0 and 100."
            )

        data["suitability_score"] = score

        recommendation = str(
            data["recommendation"]
        ).strip().capitalize()

        if recommendation not in {"Apply", "Consider", "Skip"}:
            raise ValueError(
                "Recommendation must be Apply, Consider, or Skip."
            )

        data["recommendation"] = recommendation

        # Location is assessed separately for each listing.
        for field in self.LOCATION_FIELDS:
            data.pop(field, None)

        for field in (
            "matching_skills",
            "missing_skills",
            "concerns",
        ):
            if field in data and not isinstance(data[field], list):
                data[field] = [str(data[field])]

        return data

    def _build_role_analysis_prompt(self, job):
        context = self.get_profile_context()

        profile = context["profile"]
        lessons = context["previous_learning"]

        # Exclude location so analysis can be shared between listings.
        role_job = dict(job)

        for field in self.LOCATION_FIELDS:
            role_job.pop(field, None)

        for field in ("location", "state", "country"):
            role_job.pop(field, None)

        return f"""
Analyze this job for the candidate based on role fit only.

CANDIDATE PROFILE:
{json.dumps(profile, indent=2, default=str)}

PREVIOUS LEARNING:
{json.dumps(lessons, indent=2, default=str)}

JOB ROLE DETAILS:
{json.dumps(role_job, indent=2, default=str)}

Rules:
- Evaluate skills, experience, responsibilities, and career relevance.
- Do not assess city, commute, relocation, or remote eligibility.
- Do not assume skills or qualifications not in the profile.
- Treat the candidate as a Python-focused fresher unless
  the profile explicitly says otherwise.
- Do not invent professional experience or certifications.
- Do not assume the candidate knows Java, C, or other languages
  unless listed in the profile.
- A high score does not guarantee selection.
- Keep the response concise and factual.
- Return valid JSON only.
- Do not include Markdown code fences.

Return this JSON structure:

{{
  "job_title": "Job title",
  "company": "Company name",
  "suitability_score": 0,
  "recommendation": "Apply",
  "summary": "Brief explanation",
  "matching_skills": [],
  "missing_skills": [],
  "experience_match": "Good, Partial, or Poor",
  "career_relevance": "Brief explanation",
  "concerns": []
}}

Recommendation must be Apply, Consider, or Skip.
Score must be an integer from 0 to 100.
""".strip()

    def _generate_analysis(self, prompt):
        """Generate analysis and retry once if the response is invalid."""

        system_prompt = (
            "You are a careful job suitability analyst. "
            "Be honest and conservative. "
            "Never invent candidate qualifications. "
            "Return valid JSON only."
        )

        response = self.ai.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1800,
            temperature=0.1,
        )

        try:
            return self._parse_json_response(response)

        except ValueError as first_error:
            # One correction attempt. This uses the same free provider.
            retry_prompt = f"""
Your previous response was invalid or incomplete.

Error:
{first_error}

Return a complete, valid JSON object matching the original
requested structure.

Do not add Markdown or explanatory text.

Original task:
{prompt}
""".strip()

            response = self.ai.generate(
                prompt=retry_prompt,
                system_prompt=system_prompt,
                max_tokens=1800,
                temperature=0,
            )

            return self._parse_json_response(response)

    @staticmethod
    def _normalize_location(location):
        text = str(location or "").lower().strip()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _remote_country_scope(job):
        """Identify remote eligibility only when listing evidence supports it."""

        explicit_country_list = (
            job.get("eligible_countries")
            or job.get("remote_countries")
        )

        eligibility_text = str(
            job.get("remote_eligibility") or ""
        ).lower()

        if isinstance(
            explicit_country_list,
            (list, tuple, set),
        ):
            list_text = " ".join(
                str(item) for item in explicit_country_list
            )
        else:
            list_text = str(explicit_country_list or "")

        text = f"{eligibility_text} {list_text}".lower().strip()

        if not text:
            return "Unknown"

        if any(
            token in text
            for token in (
                "worldwide",
                "anywhere",
                "global",
                "all countries",
            )
        ):
            return "Worldwide"

        if "india" in text or "indian" in text:
            return "India"

        if explicit_country_list:
            return "Other specified countries"

        if any(
            token in eligibility_text
            for token in (
                "only",
                "within",
                "based in",
                "us-only",
                "uk-only",
                "europe only",
            )
        ):
            return "Other specified countries"

        return "Unknown"

    def assess_listing_location(self, job):
        """Assess location separately for each individual listing."""

        preferences = job_search.get_search_preferences()
        preferred_locations = preferences.get("locations", [])

        job_location = str(job.get("location") or "").strip()
        state = str(job.get("state") or "").strip()
        country = str(job.get("country") or "").strip()
        work_mode = str(job.get("work_mode") or "").strip()

        remote_flag = (
            job.get("remote") is True
            or job.get("is_remote") is True
        )

        location_text = self._normalize_location(
            " ".join(
                item
                for item in (job_location, state, country)
                if item
            )
        )

        mode_text = self._normalize_location(work_mode)

        is_remote = (
            remote_flag
            or "remote" in mode_text
            or "remote" in location_text
        )

        remote_scope = (
            self._remote_country_scope(job)
            if is_remote
            else "Not remote"
        )

        matched = []
        remote_india_match = False
        remote_india_unknown = False
        global_remote_match = False
        global_remote_unknown = False

        for preference in preferred_locations:
            pref = self._normalize_location(preference)

            if not pref:
                continue

            if pref == "remote india":
                if not is_remote:
                    continue

                if remote_scope in {"India", "Worldwide"}:
                    matched.append(preference)
                    remote_india_match = True

                elif remote_scope == "Other specified countries":
                    continue

                else:
                    remote_india_unknown = True

                continue

            if pref == "global remote":
                if not is_remote:
                    continue

                if remote_scope == "Worldwide":
                    matched.append(preference)
                    global_remote_match = True

                elif remote_scope == "Other specified countries":
                    continue

                else:
                    global_remote_unknown = True

                continue

            # Kerala state-wide preference.
            if pref == "kerala" and (
                "kerala" in location_text
                or "kerala" in self._normalize_location(state)
            ):
                matched.append(preference)
                continue

            # Token-based matching avoids accidental substring matches.
            if re.search(
                rf"(?:^|\s){re.escape(pref)}(?:$|\s)",
                location_text,
            ):
                matched.append(preference)

        if is_remote:
            if remote_india_match:
                status = "Remote — India eligible"
                location_match = True

            elif global_remote_match:
                status = "Remote — worldwide"
                location_match = True

            elif remote_india_unknown or global_remote_unknown:
                status = "Remote — eligibility scope unknown"
                location_match = None

            elif remote_scope == "India":
                status = "Remote — India eligible"
                location_match = True

            elif remote_scope == "Worldwide":
                status = "Remote — worldwide"
                location_match = True

            elif remote_scope == "Other specified countries":
                status = "Remote — India eligibility not listed"
                location_match = False

            else:
                status = "Remote — country eligibility not specified"
                location_match = None

        elif matched:
            status = "Preferred location"
            location_match = True

        elif not job_location and not state:
            status = "Location unknown"
            location_match = None

        else:
            status = "Outside preferred locations"
            location_match = False

        return {
            "job_location": job_location,
            "state": state,
            "country": country,
            "work_mode": work_mode or "Unknown",
            "is_remote": is_remote,
            "remote_scope": remote_scope,
            "location_match": location_match,
            "location_status": status,
            "matched_preferences": matched,
        }

    def analyze_job(self, job):
        actual_job = self._extract_job(job)

        prompt = self._build_role_analysis_prompt(actual_job)
        role_analysis = self._generate_analysis(prompt)

        return {
            "job": actual_job,
            "analysis": role_analysis,
            "listing_assessment": self.assess_listing_location(
                actual_job
            ),
        }

    def analyze_jobs(self, jobs):
        results = []

        for job in jobs:
            try:
                results.append(self.analyze_job(job))

            except Exception as exc:
                results.append({
                    "job": self._extract_job(job),
                    "analysis": None,
                    "listing_assessment": None,
                    "error": str(exc),
                })

        return results


job_analyzer = JobAnalyzer()
