"""Tests for Confluence MCP models."""

from confluence_mcp_server.models import ConfluenceAPIError


class TestConfluenceAPIError:
    def test_basic_error(self) -> None:
        err = ConfluenceAPIError("Something went wrong")
        assert str(err) == "Something went wrong"
        assert err.errors == []

    def test_error_with_errors_list(self) -> None:
        errors = ["field1 is required", "field2 is invalid"]
        err = ConfluenceAPIError("Validation failed", errors=errors)
        assert str(err) == "Validation failed"
        assert err.errors == errors

    def test_error_with_none_errors(self) -> None:
        err = ConfluenceAPIError("Oops", errors=None)
        assert err.errors == []

    def test_is_exception(self) -> None:
        err = ConfluenceAPIError("test")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with __import__("pytest").raises(ConfluenceAPIError, match="boom"):
            raise ConfluenceAPIError("boom")

    def test_error_with_empty_errors_list(self) -> None:
        err = ConfluenceAPIError("empty", errors=[])
        assert err.errors == []
