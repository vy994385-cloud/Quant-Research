"""Tests for business profile data model."""

from datetime import date, datetime, timezone

import pytest

from src.data.company.business_profile import BusinessProfile


class TestBusinessProfileModel:
    def test_minimal_profile(self):
        profile = BusinessProfile(symbol="TEST")
        assert profile.symbol == "TEST"
        assert profile.sector is None
        assert profile.industry is None
        assert profile.country is None
        assert profile.full_time_employees is None
        assert profile.business_summary is None
        assert profile.website is None

    def test_full_profile(self):
        profile = BusinessProfile(
            symbol="TEST",
            company_name="Test Corp",
            sector="Technology",
            industry="Software",
            country="US",
            full_time_employees=5000,
            business_summary="A test company.",
            website="https://test.com",
            source_name="yahoo_finance",
            source_type="PROFILE",
        )
        assert profile.symbol == "TEST"
        assert profile.company_name == "Test Corp"
        assert profile.sector == "Technology"
        assert profile.industry == "Software"
        assert profile.country == "US"
        assert profile.full_time_employees == 5000

    def test_has_sector_true(self):
        profile = BusinessProfile(symbol="T", sector="Technology")
        assert profile.has_sector is True

    def test_has_sector_false(self):
        profile = BusinessProfile(symbol="T")
        assert profile.has_sector is False

    def test_has_sector_empty_string(self):
        profile = BusinessProfile(symbol="T", sector="")
        assert profile.has_sector is False

    def test_has_industry_true(self):
        profile = BusinessProfile(symbol="T", industry="Software")
        assert profile.has_industry is True

    def test_has_industry_false(self):
        profile = BusinessProfile(symbol="T")
        assert profile.has_industry is False

    def test_has_employees_true(self):
        profile = BusinessProfile(symbol="T", full_time_employees=100)
        assert profile.has_employees is True

    def test_has_employees_false(self):
        profile = BusinessProfile(symbol="T")
        assert profile.has_employees is False

    def test_has_business_summary_true(self):
        profile = BusinessProfile(symbol="T", business_summary="A company.")
        assert profile.has_business_summary is True

    def test_has_business_summary_false(self):
        profile = BusinessProfile(symbol="T")
        assert profile.has_business_summary is False

    def test_has_business_summary_empty(self):
        profile = BusinessProfile(symbol="T", business_summary="")
        assert profile.has_business_summary is False

    def test_coverage_fields(self):
        profile = BusinessProfile(
            symbol="T",
            company_name="Test",
            sector="Tech",
            industry="Software",
        )
        coverage = profile.coverage_fields
        assert "company_name" in coverage
        assert "sector" in coverage
        assert "industry" in coverage
        assert "country" not in coverage
        assert "full_time_employees" not in coverage

    def test_missing_fields(self):
        profile = BusinessProfile(symbol="T")
        missing = profile.missing_fields
        assert "company_name" in missing
        assert "sector" in missing
        assert "industry" in missing
        assert "country" in missing
        assert "full_time_employees" in missing
        assert "business_summary" in missing
        assert "website" in missing

    def test_coverage_fields_all_populated(self):
        profile = BusinessProfile(
            symbol="T",
            company_name="Test",
            sector="Tech",
            industry="Software",
            country="US",
            full_time_employees=100,
            business_summary="A test company.",
            website="https://test.com",
        )
        assert len(profile.coverage_fields) == 7
        assert len(profile.missing_fields) == 0

    def test_forbids_extra_fields(self):
        with pytest.raises(Exception):
            BusinessProfile(symbol="T", unknown_field="value")

    def test_zero_employees_valid(self):
        profile = BusinessProfile(symbol="T", full_time_employees=0)
        assert profile.full_time_employees == 0
        assert profile.has_employees is True

    def test_negative_employees_invalid(self):
        with pytest.raises(Exception):
            BusinessProfile(symbol="T", full_time_employees=-1)

    def test_serialization_roundtrip(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Technology",
            industry="Software",
        )
        data = profile.model_dump()
        restored = BusinessProfile(**data)
        assert restored.symbol == profile.symbol
        assert restored.sector == profile.sector
