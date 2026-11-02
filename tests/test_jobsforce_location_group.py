"""Tests proving role analysis is location-neutral and listing checks stay local."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.job_analyzer import JobAnalyzer


class FakeAI:
    def generate(self, prompt, system_prompt=None, **kwargs):
        # Deliberately includes legacy location fields: parser must remove them.
        return '''{
          "job_title": "Python Developer",
          "company": "Example Co",
          "suitability_score": 80,
          "recommendation": "Apply",
          "summary": "Python role fits the candidate",
          "matching_skills": ["Python"],
          "missing_skills": [],
          "location_match": "Perfect",
          "remote_eligibility": "India"
        }'''


def test_role_analysis_does_not_keep_location_specific_ai_fields():
    analyzer = JobAnalyzer(ai=FakeAI())
    result = analyzer.analyze_job({
        "title": "Python Developer", "company": "Example Co",
        "location": "Kochi", "work_mode": "On-site",
    })
    assert "location_match" not in result["analysis"]
    assert "remote_eligibility" not in result["analysis"]
    assert result["listing_assessment"]["location_match"] is True


def test_remote_location_is_unknown_without_explicit_country_eligibility():
    analyzer = JobAnalyzer(ai=FakeAI())
    assessment = analyzer.assess_listing_location({
        "location": "Remote", "work_mode": "Remote", "country": "India"
    })
    assert assessment["is_remote"] is True
    assert assessment["remote_scope"] == "Unknown"
    assert assessment["location_match"] is None
    assert "unknown" in assessment["location_status"].lower()


def test_remote_india_explicitly_eligible_is_match():
    analyzer = JobAnalyzer(ai=FakeAI())
    assessment = analyzer.assess_listing_location({
        "location": "Remote", "work_mode": "Remote",
        "remote_eligibility": "India",
    })
    assert assessment["remote_scope"] == "India"
    assert assessment["location_match"] is True
    assert "Remote India" in assessment["matched_preferences"]
