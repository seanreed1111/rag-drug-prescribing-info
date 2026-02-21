"""Unit tests for ingest_pdfs retry helpers."""

from parser_v1.scripts.ingest_pdfs import _is_rate_limit_error


def test_rate_limit_in_message():
    assert _is_rate_limit_error(Exception("rate limit exceeded")) is True


def test_429_in_message():
    assert _is_rate_limit_error(Exception("HTTP 429 Too Many Requests")) is True


def test_too_many_requests_in_message():
    assert _is_rate_limit_error(Exception("too many requests, slow down")) is True


def test_rate_underscore_limit_in_message():
    assert _is_rate_limit_error(Exception("rate_limit error from API")) is True


def test_chained_cause_is_rate_limit():
    inner = Exception("429 rate limit")
    outer = Exception("embedding failed")
    outer.__cause__ = inner
    assert _is_rate_limit_error(outer) is True


def test_non_rate_limit_error_returns_false():
    assert _is_rate_limit_error(ValueError("invalid input")) is False


def test_auth_error_not_retried():
    assert _is_rate_limit_error(Exception("401 Unauthorized")) is False


def test_empty_message_returns_false():
    assert _is_rate_limit_error(Exception("")) is False
