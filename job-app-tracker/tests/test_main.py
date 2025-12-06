# tests/test_main.py
"""Unit tests for main.py functionality."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import normalize_status, parse_classification_details


class TestNormalizeStatus:
    """Tests for the normalize_status function."""

    def test_declined_variations(self):
        """Test that various decline-related terms are normalized to 'Declined'."""
        assert normalize_status("declined") == "Declined"
        assert normalize_status("Rejected") == "Declined"
        assert normalize_status("not selected for this position") == "Declined"
        assert normalize_status("Unfortunately, we have decided not to move forward") == "Declined"
        assert normalize_status("We regret to inform you") == "Declined"

    def test_offer_variations(self):
        """Test that offer-related terms are normalized to 'Offer'."""
        assert normalize_status("offer") == "Offer"
        assert normalize_status("Offer Extended") == "Offer"
        assert normalize_status("accepted") == "Offer"
        assert normalize_status("Congratulations! You've been selected") == "Offer"
        assert normalize_status("We are pleased to offer you") == "Offer"

    def test_interviewed_variations(self):
        """Test that interview-related terms are normalized to 'Interviewed'."""
        assert normalize_status("interview") == "Interviewed"
        assert normalize_status("Interview Scheduled") == "Interviewed"
        assert normalize_status("phone screening") == "Interviewed"
        assert normalize_status("We'd like to schedule a phone call") == "Interviewed"

    def test_applied_variations(self):
        """Test that application-related terms are normalized to 'Applied'."""
        assert normalize_status("applied") == "Applied"
        assert normalize_status("Application Submitted") == "Applied"
        assert normalize_status("received your application") == "Applied"
        assert normalize_status("Thank you for applying") == "Applied"

    def test_unknown_defaults_to_applied(self):
        """Test that unknown statuses default to 'Applied'."""
        assert normalize_status("Unknown") == "Applied"
        assert normalize_status("unknown") == "Applied"
        assert normalize_status("") == "Applied"
        assert normalize_status("some random text") == "Applied"

    def test_case_insensitivity(self):
        """Test that status normalization is case-insensitive."""
        assert normalize_status("DECLINED") == "Declined"
        assert normalize_status("OFFER") == "Offer"
        assert normalize_status("INTERVIEW") == "Interviewed"
        assert normalize_status("APPLIED") == "Applied"

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled."""
        assert normalize_status("  declined  ") == "Declined"
        assert normalize_status("\toffer\n") == "Offer"


class TestParseClassificationDetails:
    """Tests for the parse_classification_details function."""

    def test_valid_classification(self):
        """Test parsing a valid classification response."""
        classification = """Company: Acme Corp
Job Title: Software Engineer
Location: San Francisco, CA
Status: Applied"""

        result = parse_classification_details(classification)

        assert result["Company"] == "Acme Corp"
        assert result["Job Title"] == "Software Engineer"
        assert result["Location"] == "San Francisco, CA"
        assert result["status"] == "Applied"
        assert result["Date"] == ""  # Date is set separately

    def test_declined_status_normalization(self):
        """Test that status is normalized during parsing."""
        classification = """Company: Test Inc
Job Title: Data Analyst
Location: Remote
Status: Unfortunately, we have decided not to move forward"""

        result = parse_classification_details(classification)
        assert result["status"] == "Declined"

    def test_unknown_fields(self):
        """Test handling of Unknown field values."""
        classification = """Company: Unknown
Job Title: Unknown
Location: Unknown
Status: Unknown"""

        result = parse_classification_details(classification)

        assert result["Company"] == "Unknown"
        assert result["Job Title"] == "Unknown"
        assert result["Location"] == "Unknown"
        assert result["status"] == "Applied"  # Unknown status defaults to Applied

    def test_empty_classification(self):
        """Test handling of empty classification."""
        result = parse_classification_details("")

        assert result["Company"] == ""
        assert result["Job Title"] == ""
        assert result["Location"] == ""
        assert result["status"] == ""
        assert result["Date"] == ""

    def test_partial_classification(self):
        """Test handling of partial classification with missing fields."""
        classification = """Company: Partial Corp
Job Title: Engineer"""

        result = parse_classification_details(classification)

        assert result["Company"] == "Partial Corp"
        assert result["Job Title"] == "Engineer"
        assert result["Location"] == ""
        assert result["status"] == ""

    def test_case_insensitive_field_names(self):
        """Test that field names are case-insensitive."""
        classification = """COMPANY: Upper Corp
JOB TITLE: Manager
LOCATION: NYC
STATUS: Offer"""

        result = parse_classification_details(classification)

        assert result["Company"] == "Upper Corp"
        assert result["Job Title"] == "Manager"
        assert result["Location"] == "NYC"
        assert result["status"] == "Offer"

    def test_extra_whitespace(self):
        """Test handling of extra whitespace in values."""
        classification = """Company:   Spacey Corp
Job Title:   Developer
Location:   Boston, MA
Status:   Applied   """

        result = parse_classification_details(classification)

        assert result["Company"] == "Spacey Corp"
        assert result["Job Title"] == "Developer"
        assert result["Location"] == "Boston, MA"
        assert result["status"] == "Applied"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
