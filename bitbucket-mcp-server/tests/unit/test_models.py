"""Tests for Bitbucket MCP Server models."""

from bitbucket_mcp_server.models import BitbucketAPIError


class TestBitbucketAPIError:
    def test_basic_creation(self) -> None:
        err = BitbucketAPIError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.errors == []

    def test_with_errors_list(self) -> None:
        err = BitbucketAPIError("bad request", errors=["field1 invalid", "field2 missing"])
        assert str(err) == "bad request"
        assert err.errors == ["field1 invalid", "field2 missing"]

    def test_none_errors_defaults_to_empty_list(self) -> None:
        err = BitbucketAPIError("fail", errors=None)
        assert err.errors == []

    def test_is_exception(self) -> None:
        err = BitbucketAPIError("test")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with __import__("pytest").raises(BitbucketAPIError, match="oops"):
            raise BitbucketAPIError("oops")
