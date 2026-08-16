"""Unit tests for email normalization (app/utils/email.py)."""

from app.utils.email import normalize_email


def test_normalize_email_lowercases():
    assert normalize_email("USER@EXAMPLE.GOV") == "user@example.gov"


def test_normalize_email_strips_surrounding_whitespace():
    assert normalize_email("  user@example.gov  ") == "user@example.gov"


def test_normalize_email_is_idempotent():
    once = normalize_email("  User@Example.Gov ")
    twice = normalize_email(once)
    assert once == twice == "user@example.gov"
