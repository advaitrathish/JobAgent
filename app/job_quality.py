
"""Quality scoring and filtering for JobAgent job listings."""

import re
from copy import deepcopy


class JobQualityFilter:
    """Score job listings against the candidate's preferences and skills."""

    # Technical roles relevant to the candidate's career interests.
    TECHNICAL_ROLE_KEYWORDS = {
        "python",
        "software developer",
        "software engineer",
        "software development",
        "backend developer",
        "backend engineer",
        "full stack",
        "fullstack",
        "web developer",
        "web development",
        "ai developer",
        "ai engineer",
        "artificial intelligence",
        "machine learning",
        "ml engineer",
        "generative ai",
        "genai",
        "llm engineer",
        "automation developer",
        "application developer",
        "technical intern",
        "developer intern",
        "software intern",
        "backend intern",
        "python intern",
    }

    # Clearly unrelated job categories.
    IRRELEVANT_ROLE_KEYWORDS = {
        "marketing",
        "digital marketing",
        "marketing associate",
        "sales",
        "sales associate",
        "business development",
        "telecaller",
        "telemarketing",
        "customer support",
        "customer service",
        "recruiter",
        "recruitment",
        "human resources",
        "hr executive",
        "accountant",
        "accounting",
        "finance associate",
        "financial advisor",
        "content writer",
        "copywriter",
        "social media manager",
        "graphic designer",
        "video editor",
        "data entry",
        "operations associate",
        "administrative assistant",
    }

    ENTRY_LEVEL_KEYWORDS = {
        "fresher",
        "freshers",
        "entry level",
        "entry-level",
        "junior",
        "intern",
        "internship",
        "graduate",
        "trainee",
        "0-1 year",
        "0-2 years",
        "no experience",
    }

    CONFIDENTIAL_COMPANY_KEYWORDS = {
        "confidential",
        "undisclosed",
        "private client",
        "stealth startup",
        "anonymous employer",
    }

    def __init__(
        self,
        preferred_roles=None,
        preferred_locations=None,
        skills=None,
        max_per_known_company=2,
        max_per_role=3,
        minimum_score=30,
    ):
        self.preferred_roles = preferred_roles or []
        self.preferred_locations = preferred_locations or []
        self.skills = skills or ["Python", "AI", "GenAI"]

        self.max_per_known_company = max_per_known_company

        # Retained for backwards compatibility with existing workflow code.
        # Different listings of the same role are not automatically duplicates.
        self.max_per_role = max_per_role

        self.minimum_score = minimum_score

        self._normalize_preferences()

    @staticmethod
    def _normalize_text(value):
        """Normalize text for comparisons."""

        if not value:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(value).lower().strip(),
        )

    @staticmethod
    def _contains_phrase(text, phrase):
        """Match a phrase without accidental partial-word matches."""

        text = JobQualityFilter._normalize_text(text)
        phrase = JobQualityFilter._normalize_text(phrase)

        if not text or not phrase:
            return False

        pattern = (
            r"(?<![a-zA-Z0-9])"
            + re.escape(phrase)
            + r"(?![a-zA-Z0-9])"
        )

        return bool(re.search(pattern, text))

    def _normalize_preferences(self):
        """Clean user preferences."""

        self.preferred_roles = [
            str(role).strip()
            for role in self.preferred_roles
            if role and str(role).strip()
        ]

        self.preferred_locations = [
            str(location).strip()
            for location in self.preferred_locations
            if location and str(location).strip()
        ]

        self.skills = [
            str(skill).strip()
            for skill in self.skills
            if skill and str(skill).strip()
        ]

    @staticmethod
    def _get_job_text(job):
        """Collect title and description fields."""

        fields = [
            job.get("title", ""),
            job.get("summary", ""),
            job.get("description", ""),
            job.get("job_description", ""),
            job.get("requirements", ""),
            job.get("skills_required", ""),
            job.get("category", ""),
        ]

        return " ".join(
            str(field)
            for field in fields
            if field
        )

    @staticmethod
    def _get_title(job):
        return str(
            job.get("title", "")
            or job.get("job_title", "")
        ).strip()

    @staticmethod
    def _get_company(job):
        return str(
            job.get("company", "")
            or job.get("company_name", "")
        ).strip()

    @staticmethod
    def _get_location(job):
        return str(
            job.get("location", "")
            or job.get("city", "")
        ).strip()

    def _is_confidential_company(self, job):
        """Detect anonymous employers without assuming their identity."""

        company = self._normalize_text(
            self._get_company(job)
        )

        if job.get("company_confidential") is True:
            return True

        return any(
            keyword in company
            for keyword in self.CONFIDENTIAL_COMPANY_KEYWORDS
        )

    def _is_technical_role(self, title):
        """Check whether the role belongs to the candidate's technical focus."""

        normalized_title = self._normalize_text(title)

        if not normalized_title:
            return False

        # A clear technical title takes precedence over generic keywords.
        if any(
            self._contains_phrase(normalized_title, keyword)
            for keyword in self.TECHNICAL_ROLE_KEYWORDS
        ):
            return True

        return False

    def _is_irrelevant_role(self, title):
        """Reject clearly unrelated roles."""

        normalized_title = self._normalize_text(title)

        if not normalized_title:
            return True

        # A technical title should not be rejected just because its description
        # mentions unrelated departments or responsibilities.
        if self._is_technical_role(normalized_title):
            return False

        return any(
            self._contains_phrase(normalized_title, keyword)
            for keyword in self.IRRELEVANT_ROLE_KEYWORDS
        )

    def _matches_preferred_role(self, title):
        """Match the job title to one or more preferred role names."""

        normalized_title = self._normalize_text(title)

        for role in self.preferred_roles:
            normalized_role = self._normalize_text(role)

            if not normalized_role:
                continue

            if normalized_role in normalized_title:
                return True

            # Broad technical role family matching.
            if (
                "python" in normalized_role
                and "python" in normalized_title
            ):
                return True

            if (
                "backend" in normalized_role
                and "backend" in normalized_title
            ):
                return True

            if (
                "full stack" in normalized_role
                and (
                    "full stack" in normalized_title
                    or "fullstack" in normalized_title
                )
            ):
                return True

            if (
                "software developer" in normalized_role
                and (
                    "software developer" in normalized_title
                    or "software engineer" in normalized_title
                )
            ):
                return True

            if (
                "ai" in normalized_role
                and (
                    "ai" in normalized_title
                    or "artificial intelligence" in normalized_title
                )
            ):
                return True

        return False

    def _match_skills(self, job):
        """Find candidate skills mentioned in the job listing."""

        job_text = self._normalize_text(
            self._get_job_text(job)
        )

        matched_skills = []

        for skill in self.skills:
            normalized_skill = self._normalize_text(skill)

            if not normalized_skill:
                continue

            if self._contains_phrase(
                job_text,
                normalized_skill,
            ):
                matched_skills.append(skill)

        return matched_skills

    def _is_entry_level(self, job):
        """Check whether the listing appears suitable for freshers."""

        title = self._normalize_text(
            self._get_title(job)
        )

        description = self._normalize_text(
            self._get_job_text(job)
        )

        experience = self._normalize_text(
            job.get("experience", "")
            or job.get("experience_required", "")
        )

        text = " ".join([
            title,
            description,
            experience,
        ])

        return any(
            keyword in text
            for keyword in self.ENTRY_LEVEL_KEYWORDS
        )

    def _matches_location(self, job):
        """Check location preference, including remote listings."""

        location = self._normalize_text(
            self._get_location(job)
        )

        work_mode = self._normalize_text(
            job.get("work_mode", "")
        )

        remote_scope = self._normalize_text(
            job.get("remote_scope", "")
        )

        remote_eligibility = self._normalize_text(
            job.get("remote_eligibility", "")
        )

        is_remote = (
            "remote" in work_mode
            or "remote" in location
            or "remote" in remote_scope
        )

        for preferred_location in self.preferred_locations:
            preferred = self._normalize_text(
                preferred_location
            )

            if not preferred:
                continue

            # Remote India is not the same as global remote.
            if preferred == "remote india":
                if (
                    is_remote
                    and (
                        "india" in location
                        or "india" in remote_scope
                        or "india" in remote_eligibility
                        or "india" in work_mode
                    )
                ):
                    return True

            elif preferred == "global remote":
                if (
                    is_remote
                    and (
                        "global" in location
                        or "global" in remote_scope
                        or "worldwide" in remote_eligibility
                        or "worldwide" in location
                    )
                ):
                    return True

            elif self._contains_phrase(
                location,
                preferred,
            ):
                return True

        return False

    def score_job(self, job):
        """Return a quality score and reasons for an individual listing."""

        title = self._get_title(job)
        company = self._get_company(job)
        location = self._get_location(job)

        job_text = self._normalize_text(
            self._get_job_text(job)
        )

        score = 0
        reasons = []

        matched_skills = self._match_skills(job)

        confidential = self._is_confidential_company(job)

        role_match = self._matches_preferred_role(title)

        technical_role = self._is_technical_role(title)

        entry_level = self._is_entry_level(job)

        location_match = self._matches_location(job)

        irrelevant_role = self._is_irrelevant_role(title)

        # Clearly unrelated roles should not survive filtering.
        if irrelevant_role:
            return {
                "quality_score": 0,
                "quality_reasons": [
                    "Job role is unrelated to the candidate's technical career goals"
                ],
                "company_confidential": confidential,
                "matched_skills": matched_skills,
                "location_match": location_match,
                "role_relevant": False,
                "quality_rejected": True,
            }

        # Preferred job title.
        if role_match:
            score += 25
            reasons.append("Matches a preferred job role")

        elif technical_role:
            score += 20
            reasons.append("Matches the candidate's technical career interests")

        else:
            score -= 15
            reasons.append("Job title has limited technical relevance")

        # Skills.
        if matched_skills:
            skill_points = min(
                len(matched_skills) * 10,
                30,
            )

            score += skill_points

            reasons.append(
                "Relevant skills: "
                + ", ".join(matched_skills)
            )

        # Entry-level suitability.
        if entry_level:
            score += 20
            reasons.append(
                "Appears suitable for entry-level candidates"
            )

        # Location.
        if location_match:
            score += 15
            reasons.append(
                "Matches a preferred location"
            )

        elif location:
            score -= 5
            reasons.append(
                "Location is not explicitly preferred"
            )

        # Description quality.
        description = str(
            job.get("summary", "")
            or job.get("description", "")
            or job.get("job_description", "")
        ).strip()

        if len(description) < 100:
            score -= 10
            reasons.append(
                "Job description contains limited detail"
            )

        else:
            score += 5
            reasons.append(
                "Job description provides useful details"
            )

        # Employer transparency.
        if confidential:
            reasons.append(
                "Employer identity is confidential"
            )

        elif company:
            score += 5
            reasons.append(
                "Employer identity is available"
            )

        # Remote work should not automatically imply global eligibility.
        if (
            "remote" in self._normalize_text(
                job.get("work_mode", "")
            )
        ):
            reasons.append(
                "Remote eligibility should be verified from the listing"
            )

        score = max(
            0,
            min(100, score),
        )

        return {
            "quality_score": score,
            "quality_reasons": reasons,
            "company_confidential": confidential,
            "matched_skills": matched_skills,
            "location_match": location_match,
            "role_relevant": technical_role or role_match,
            "quality_rejected": False,
        }

    def _get_duplicate_key(self, job):
        """Use listing identity rather than title alone."""

        source_id = (
            job.get("source_id")
            or job.get("job_id")
            or job.get("id")
        )

        if source_id:
            return (
                str(job.get("source", "")).lower(),
                str(source_id).strip().lower(),
            )

        url = (
            job.get("job_url")
            or job.get("apply_url")
            or job.get("url")
        )

        if url:
            return (
                "url",
                str(url).strip().lower(),
            )

        # Only consider listings duplicates when the title, company,
        # and location all match.
        return (
            self._normalize_text(self._get_title(job)),
            self._normalize_text(self._get_company(job)),
            self._normalize_text(self._get_location(job)),
        )

    def filter_and_rank(self, jobs):
        """Filter irrelevant jobs, remove exact duplicates, and rank results."""

        if not jobs:
            return []

        scored_jobs = []
        seen_listing_keys = set()

        company_counts = {}

        for original_job in jobs:
            if not isinstance(original_job, dict):
                continue

            job = deepcopy(original_job)

            quality = self.score_job(job)

            job.update(quality)

            if quality["quality_rejected"]:
                continue

            if quality["quality_score"] < self.minimum_score:
                continue

            duplicate_key = self._get_duplicate_key(job)

            if duplicate_key in seen_listing_keys:
                continue

            seen_listing_keys.add(duplicate_key)

            company = self._normalize_text(
                self._get_company(job)
            )

            confidential = quality["company_confidential"]

            # Do not impose a company cap on anonymous employers.
            # Different confidential postings may belong to different companies.
            if (
                company
                and not confidential
                and self.max_per_known_company
            ):
                current_count = company_counts.get(
                    company,
                    0,
                )

                if current_count >= self.max_per_known_company:
                    continue

                company_counts[company] = current_count + 1

            scored_jobs.append(job)

        # Highest quality first.
        scored_jobs.sort(
            key=lambda job: (
                job.get("quality_score", 0),
                job.get("location_match", False),
            ),
            reverse=True,
        )

        return scored_jobs
