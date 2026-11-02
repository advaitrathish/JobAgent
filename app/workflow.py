
"""Coordinates job search, quality ranking, tracking, listing checks, and AI analysis."""

from app.job_quality import JobQualityFilter
from app.job_search import job_search
from app.application_tracker import application_tracker
from app.job_analyzer import job_analyzer
from app.agent import job_agent


MAX_ANALYSES_PER_RUN = 5


class JobWorkflow:
    def __init__(
        self,
        job_source=None,
        tracker=None,
        analyzer=None,
        agent=None,
        quality_filter=None,
    ):
        self.job_source = job_source
        self.tracker = tracker or application_tracker
        self.analyzer = analyzer or job_analyzer
        self.agent = agent or job_agent

        self.quality_filter = quality_filter or self._create_quality_filter()

    def _create_quality_filter(self):
        """Create a quality filter using the user's profile preferences."""

        preferences = job_search.get_search_preferences()

        profile = {}

        try:
            profile = self.analyzer.get_profile_context().get(
                "profile", {}
            )
        except Exception:
            profile = {}

        skills = profile.get("skills", {})
        skill_names = []

        if isinstance(skills, dict):
            for value in skills.values():
                if isinstance(value, list):
                    skill_names.extend(value)
                elif isinstance(value, str):
                    skill_names.append(value)

        elif isinstance(skills, list):
            skill_names.extend(skills)

        return JobQualityFilter(
            preferred_roles=preferences.get("roles", []),
            preferred_locations=preferences.get("locations", []),
            skills=skill_names or ["Python", "AI", "GenAI"],
            max_per_known_company=2,
            max_per_role=3,
        )

    def run(self, user_request):
        """Keep compatibility with the project's simple conversational test."""
        return self.agent.respond(user_request)

    @staticmethod
    def _application_from_tracker_result(result):
        if isinstance(result, dict):
            return (
                result.get("application", result),
                result.get("added", result.get("is_new", False)),
            )

        return result, True

    def rank_jobs(self, jobs):
        """Rank jobs and reduce repetitive results within the search batch."""

        if not jobs:
            return []

        ranked_jobs = self.quality_filter.filter_and_rank(jobs)

        print("\n=== Job Quality Ranking ===")
        print(f"Jobs received: {len(jobs)}")
        print(f"Jobs after quality filtering: {len(ranked_jobs)}")

        for index, job in enumerate(ranked_jobs[:10], start=1):
            company = job.get("company") or "Unknown company"

            if job.get("company_confidential"):
                company = "Confidential employer"

            print(
                f"{index}. {job.get('title', 'Unknown title')} | "
                f"{company} | "
                f"Score: {job.get('quality_score', 0)}/100"
            )

        return ranked_jobs

    def _save_listing_assessment(self, application, job):
        """Save location assessment for an individual listing."""

        assess = getattr(
            self.analyzer,
            "assess_listing_location",
            None,
        )

        if not callable(assess):
            return None

        assessment = assess(job)
        job_id = application.get("job_id")

        save_assessment = getattr(
            self.tracker,
            "save_listing_assessment",
            None,
        )

        if callable(save_assessment) and job_id:
            save_assessment(job_id, assessment)

        else:
            # Compatibility with lightweight test trackers.
            application["listing_assessment"] = assessment

        return assessment

    def _assess_group_listings(self, job_id):
        """Reassess location separately for every listing in an analysis group."""

        get_group = getattr(
            self.tracker,
            "get_group_applications",
            None,
        )

        if callable(get_group):
            applications = get_group(job_id)

        else:
            application = (
                self.tracker.get_job(job_id)
                if hasattr(self.tracker, "get_job")
                else None
            )

            applications = [application] if application else []

        assessments = []

        for application in applications:
            if not isinstance(application, dict):
                continue

            listing = application.get("job", application)

            try:
                assessment = self._save_listing_assessment(
                    application,
                    listing,
                )

                if assessment is not None:
                    assessments.append({
                        "job_id": application.get("job_id"),
                        "assessment": assessment,
                    })

            except Exception as exc:
                print(
                    "Listing assessment failed for "
                    f"{application.get('job_id', 'unknown')}: {exc}"
                )

        return assessments

    def search_and_analyze_jobs(
        self,
        per_page=10,
        max_searches=None,
    ):
        print("\n=== JobAgent Job Search Workflow ===")
        print("\nStep 1: Searching for job opportunities...")

        try:
            if self.job_source is None:
                from app.job_sources.jobsforce_india import JobsForceIndia

                self.job_source = JobsForceIndia()

            kwargs = {"per_page": per_page}

            if max_searches is not None:
                kwargs["max_searches"] = max_searches

            jobs = self.job_source.search_all_preferences(**kwargs)

        except KeyboardInterrupt:
            print("\nJob search interrupted.")

            return {
                "jobs": [],
                "ranked_jobs": [],
                "new_jobs": [],
                "analyses": [],
                "duplicates": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "interrupted": True,
            }

        except Exception as exc:
            print(f"Job search failed: {exc}")

            return {
                "jobs": [],
                "ranked_jobs": [],
                "new_jobs": [],
                "analyses": [],
                "duplicates": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "interrupted": False,
                "error": str(exc),
            }

        print(f"Jobs returned by source: {len(jobs)}")

        # Rank the search batch before adding listings to the tracker.
        ranked_jobs = self.rank_jobs(jobs)

        print(
            "\nStep 2: Save quality-filtered listings, "
            "detect duplicates, and assess locations..."
        )

        new_jobs = []
        duplicates = 0
        listing_assessments = []

        for job in ranked_jobs:
            try:
                result = self.tracker.add_job(job)

                application, is_new = (
                    self._application_from_tracker_result(result)
                )

                if is_new:
                    new_jobs.append(application)

                    print(
                        f"Saved: {job.get('title', 'Unknown title')} "
                        f"| Score: {job.get('quality_score', 0)}/100"
                    )

                else:
                    duplicates += 1

                # Location assessment is per individual listing.
                assessment = self._save_listing_assessment(
                    application,
                    job,
                )

                if assessment is not None:
                    listing_assessments.append({
                        "job_id": application.get("job_id"),
                        "assessment": assessment,
                    })

            except Exception as exc:
                print(
                    f"Could not save listing "
                    f"{job.get('title', 'Unknown title')}: {exc}"
                )

        print(f"New listings saved: {len(new_jobs)}")
        print(f"Duplicates skipped: {duplicates}")

        print("\nStep 3: Analyze pending company-role groups...")

        pending_jobs = self.tracker.get_pending_analysis(
            limit=MAX_ANALYSES_PER_RUN
        )

        print(
            f"Analysis groups selected: {len(pending_jobs)} "
            f"(max {MAX_ANALYSES_PER_RUN})"
        )

        analyses = []
        completed = 0
        failed = 0
        interrupted = False

        for index, application in enumerate(
            pending_jobs,
            start=1,
        ):
            job_id = application.get("job_id")
            job = application.get("job", application)

            print(
                f"\nAnalyzing group {index}/{len(pending_jobs)}: "
                f"{job.get('title', 'Unknown title')}"
            )

            try:
                result = self.analyzer.analyze_job(application)

                role_analysis = result.get("analysis")

                if role_analysis is None:
                    raise ValueError(
                        "Analyzer returned no role analysis."
                    )

                # Role analysis is shared across company-role group.
                self.tracker.save_analysis(
                    job_id,
                    role_analysis,
                )

                # Location assessments stay specific to each listing.
                group_assessments = self._assess_group_listings(
                    job_id
                )

                analyses.append({
                    **result,
                    "group_listing_assessments": group_assessments,
                })

                completed += 1

                print(
                    "Role analysis completed; "
                    "listing assessments refreshed."
                )

            except KeyboardInterrupt:
                print("\nAnalysis interrupted by user.")
                interrupted = True
                break

            except Exception as exc:
                failed += 1

                print(f"Analysis failed: {exc}")

                self.tracker.mark_analysis_failed(
                    job_id,
                    str(exc),
                )

                print(
                    "This group will be retried "
                    "during a future run."
                )

        print("\n=== Workflow Summary ===")

        get_summary = getattr(
            self.tracker,
            "get_summary",
            None,
        )

        if callable(get_summary):
            summary = get_summary()

            pending = summary.get(
                "pending_analysis_groups",
                0,
            )

        else:
            pending = len(
                self.tracker.get_pending_analysis(
                    limit=None
                )
            )

        print(f"Listings returned: {len(jobs)}")
        print(f"Quality-ranked listings: {len(ranked_jobs)}")
        print(f"New listings: {len(new_jobs)}")
        print(f"Duplicates: {duplicates}")
        print(f"Role analyses completed: {completed}")
        print(f"Role analyses failed: {failed}")
        print(f"Pending role-analysis groups: {pending}")

        source_errors = (
            getattr(self.job_source, "last_errors", [])
            or []
        )

        return {
            "jobs": jobs,
            "ranked_jobs": ranked_jobs,
            "new_jobs": new_jobs,
            "analyses": analyses,
            "listing_assessments": listing_assessments,
            "duplicates": duplicates,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "interrupted": interrupted,
            "source_errors": source_errors,
        }


job_workflow = JobWorkflow()
