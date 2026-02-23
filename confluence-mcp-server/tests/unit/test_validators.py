"""Tests for input validation helpers (OWASP ASVS V5)."""

import pytest

from confluence_mcp_server.validators import (
    CONTENT_TYPES,
    MOVE_POSITIONS,
    _safe_error_text,
    sanitize_cql_value,
    validate_content_id,
    validate_enum,
    validate_file_path,
    validate_link_url,
    validate_max_results,
    validate_space_key,
    validate_url_path_segment,
)


class TestValidateContentId:
    def test_valid_numeric_id(self) -> None:
        assert validate_content_id("12345") == "12345"

    def test_strips_whitespace(self) -> None:
        assert validate_content_id("  42  ") == "42"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_content_id("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_content_id("   ")

    def test_non_numeric_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a numeric string"):
            validate_content_id("abc")

    def test_mixed_alphanumeric_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a numeric string"):
            validate_content_id("12a3")

    def test_custom_name_in_error(self) -> None:
        with pytest.raises(ValueError, match="page_id must not be empty"):
            validate_content_id("", name="page_id")


class TestValidateSpaceKey:
    def test_valid_key(self) -> None:
        assert validate_space_key("DEV") == "DEV"

    def test_valid_key_with_digits_and_underscores(self) -> None:
        assert validate_space_key("TEAM_01") == "TEAM_01"

    def test_strips_whitespace(self) -> None:
        assert validate_space_key("  DEV  ") == "DEV"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_space_key("")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_space_key("A" * 256)

    def test_lowercase_raises(self) -> None:
        with pytest.raises(ValueError, match="must be uppercase"):
            validate_space_key("dev")

    def test_starts_with_digit_raises(self) -> None:
        with pytest.raises(ValueError, match="must be uppercase"):
            validate_space_key("1DEV")

    def test_special_chars_raise(self) -> None:
        with pytest.raises(ValueError, match="must be uppercase"):
            validate_space_key("DEV-TEAM")


class TestValidateMaxResults:
    def test_normal_value_returned(self) -> None:
        assert validate_max_results(25) == 25

    def test_value_capped_at_ceiling(self) -> None:
        assert validate_max_results(500) == 100

    def test_custom_ceiling(self) -> None:
        assert validate_max_results(50, ceiling=30) == 30

    def test_zero_is_valid(self) -> None:
        assert validate_max_results(0) == 0

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            validate_max_results(-1)

    def test_exact_ceiling_returned(self) -> None:
        assert validate_max_results(100) == 100


class TestValidateFilePath:
    def test_valid_file(self, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "test.txt"  # type: ignore[operator]
        f.write_text("hello")  # type: ignore[union-attr]
        result = validate_file_path(str(f))
        assert result == str(f)  # type: ignore[str-bytes-safe]

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_file_path("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_file_path("   ")

    def test_traversal_rejected(self, tmp_path: pytest.TempPathFactory) -> None:
        evil = str(tmp_path) + "/../etc/passwd"  # type: ignore[operator]
        with pytest.raises(ValueError, match="path traversal"):
            validate_file_path(evil)

    def test_nonexistent_raises(self) -> None:
        with pytest.raises(ValueError, match="File not found"):
            validate_file_path("/tmp/nonexistent_file_abc123xyz")

    def test_directory_rejected(self, tmp_path: pytest.TempPathFactory) -> None:
        with pytest.raises(ValueError, match="not a regular file"):
            validate_file_path(str(tmp_path))


class TestValidateEnum:
    def test_valid_value(self) -> None:
        result = validate_enum("page", "type", CONTENT_TYPES)
        assert result == "page"

    def test_case_insensitive_match(self) -> None:
        result = validate_enum("PAGE", "type", CONTENT_TYPES)
        assert result == "page"

    def test_mixed_case_match(self) -> None:
        result = validate_enum("Append", "position", MOVE_POSITIONS)
        assert result == "append"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError, match="must be one of"):
            validate_enum("invalid", "type", CONTENT_TYPES)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_enum("", "type", CONTENT_TYPES)

    def test_whitespace_stripped(self) -> None:
        result = validate_enum("  page  ", "type", CONTENT_TYPES)
        assert result == "page"


class TestSanitizeCqlValue:
    def test_normal_text_unchanged(self) -> None:
        assert sanitize_cql_value("hello world") == "hello world"

    def test_backslash_escaped(self) -> None:
        assert sanitize_cql_value("path\\file") == "path\\\\file"

    def test_double_quote_escaped(self) -> None:
        assert sanitize_cql_value('say "hi"') == 'say \\"hi\\"'

    def test_both_escaped(self) -> None:
        result = sanitize_cql_value('a\\b"c')
        assert result == 'a\\\\b\\"c'


class TestValidateUrlPathSegment:
    def test_normal_segment(self) -> None:
        assert validate_url_path_segment("hello") == "hello"

    def test_special_chars_encoded(self) -> None:
        result = validate_url_path_segment("hello world")
        assert result == "hello%20world"

    def test_slash_encoded(self) -> None:
        result = validate_url_path_segment("a/b")
        assert result == "a%2Fb"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_url_path_segment("")

    def test_whitespace_stripped_before_encoding(self) -> None:
        result = validate_url_path_segment("  hi  ")
        assert result == "hi"


class TestValidateLinkUrl:
    def test_valid_https(self) -> None:
        url = "https://example.com/page"
        assert validate_link_url(url) == url

    def test_valid_http(self) -> None:
        url = "http://example.com"
        assert validate_link_url(url) == url

    def test_empty_returns_empty(self) -> None:
        assert validate_link_url("") == ""

    def test_javascript_rejected(self) -> None:
        with pytest.raises(ValueError, match="Dangerous URL scheme"):
            validate_link_url("javascript:alert(1)")

    def test_data_rejected(self) -> None:
        with pytest.raises(ValueError, match="Dangerous URL scheme"):
            validate_link_url("data:text/html,<script>alert(1)</script>")

    def test_vbscript_rejected(self) -> None:
        with pytest.raises(ValueError, match="Dangerous URL scheme"):
            validate_link_url("vbscript:MsgBox")

    def test_case_insensitive_scheme_rejection(self) -> None:
        with pytest.raises(ValueError, match="Dangerous URL scheme"):
            validate_link_url("JAVASCRIPT:alert(1)")


class TestSafeErrorText:
    def test_short_text_unchanged(self) -> None:
        assert _safe_error_text("some error") == "some error"

    def test_truncated_at_max_len(self) -> None:
        long_text = "x" * 500
        result = _safe_error_text(long_text)
        assert len(result) == 200

    def test_custom_max_len(self) -> None:
        result = _safe_error_text("abcdefgh", max_len=4)
        assert result == "abcd"

    def test_bearer_token_redacted(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJIUz failed"
        result = _safe_error_text(text)
        assert "eyJhbGciOiJIUz" not in result
        assert "[REDACTED]" in result

    def test_basic_auth_redacted(self) -> None:
        text = "Basic dXNlcjpwYXNz is invalid"
        result = _safe_error_text(text)
        assert "dXNlcjpwYXNz" not in result
        assert "[REDACTED]" in result
