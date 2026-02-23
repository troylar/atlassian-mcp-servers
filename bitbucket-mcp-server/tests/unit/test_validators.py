"""Tests for Bitbucket MCP Server input validators."""

import pytest

from bitbucket_mcp_server.validators import (
    BUILD_STATES,
    PR_STATES,
    _safe_error_text,
    validate_commit_hash,
    validate_enum,
    validate_file_path,
    validate_git_ref,
    validate_max_results,
    validate_numeric_id,
    validate_positive_int,
    validate_project_key,
    validate_repo_slug,
    validate_url,
    validate_url_path_segment,
)


class TestValidateProjectKey:
    def test_valid_key(self) -> None:
        assert validate_project_key("PROJ") == "PROJ"

    def test_valid_key_with_digits(self) -> None:
        assert validate_project_key("PROJ123") == "PROJ123"

    def test_valid_key_with_underscore(self) -> None:
        assert validate_project_key("MY_PROJ") == "MY_PROJ"

    def test_strips_whitespace(self) -> None:
        assert validate_project_key("  PROJ  ") == "PROJ"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_project_key("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_project_key("   ")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_project_key("A" * 256)

    def test_lowercase_raises(self) -> None:
        with pytest.raises(ValueError, match="must be uppercase"):
            validate_project_key("proj")

    def test_starting_with_digit_raises(self) -> None:
        with pytest.raises(ValueError, match="must be uppercase"):
            validate_project_key("1PROJ")

    def test_special_chars_raises(self) -> None:
        with pytest.raises(ValueError, match="must be uppercase"):
            validate_project_key("PROJ-KEY")


class TestValidateRepoSlug:
    def test_valid_slug(self) -> None:
        assert validate_repo_slug("my-repo") == "my-repo"

    def test_valid_slug_with_dots(self) -> None:
        assert validate_repo_slug("my.repo.name") == "my.repo.name"

    def test_valid_slug_with_underscore(self) -> None:
        assert validate_repo_slug("my_repo") == "my_repo"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_repo_slug("")

    def test_bad_chars_raises(self) -> None:
        with pytest.raises(ValueError, match="must be alphanumeric"):
            validate_repo_slug("repo/name")

    def test_starting_with_hyphen_raises(self) -> None:
        with pytest.raises(ValueError, match="must be alphanumeric"):
            validate_repo_slug("-repo")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_repo_slug("a" * 256)


class TestValidateGitRef:
    def test_valid_branch(self) -> None:
        assert validate_git_ref("main") == "main"

    def test_valid_branch_with_slash(self) -> None:
        assert validate_git_ref("feature/my-branch") == "feature/my-branch"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_git_ref("")

    def test_dot_dot_traversal_raises(self) -> None:
        with pytest.raises(ValueError, match="must not contain"):
            validate_git_ref("main..develop")

    def test_space_raises(self) -> None:
        with pytest.raises(ValueError, match="contains invalid characters"):
            validate_git_ref("my branch")

    def test_tilde_raises(self) -> None:
        with pytest.raises(ValueError, match="contains invalid characters"):
            validate_git_ref("main~1")

    def test_caret_raises(self) -> None:
        with pytest.raises(ValueError, match="contains invalid characters"):
            validate_git_ref("main^2")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_git_ref("a" * 256)


class TestValidateCommitHash:
    def test_valid_full_sha(self) -> None:
        sha = "a" * 40
        assert validate_commit_hash(sha) == sha

    def test_valid_short_sha(self) -> None:
        assert validate_commit_hash("abcd") == "abcd"

    def test_valid_mixed_case(self) -> None:
        assert validate_commit_hash("aBcD1234") == "aBcD1234"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_commit_hash("")

    def test_non_hex_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a valid hex commit hash"):
            validate_commit_hash("zzzzzz")

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a valid hex commit hash"):
            validate_commit_hash("abc")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a valid hex commit hash"):
            validate_commit_hash("a" * 41)


class TestValidateNumericId:
    def test_valid(self) -> None:
        assert validate_numeric_id("123") == "123"

    def test_zero(self) -> None:
        assert validate_numeric_id("0") == "0"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_numeric_id("")

    def test_non_numeric_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a numeric string"):
            validate_numeric_id("abc")

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a numeric string"):
            validate_numeric_id("-1")


class TestValidatePositiveInt:
    def test_valid(self) -> None:
        assert validate_positive_int(1) == 1

    def test_large_value(self) -> None:
        assert validate_positive_int(9999) == 9999

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_positive_int(0)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_positive_int(-5)


class TestValidateMaxResults:
    def test_normal_value(self) -> None:
        assert validate_max_results(50) == 50

    def test_capped_at_ceiling(self) -> None:
        assert validate_max_results(200) == 100

    def test_custom_ceiling(self) -> None:
        assert validate_max_results(200, ceiling=50) == 50

    def test_zero_returns_zero(self) -> None:
        assert validate_max_results(0) == 0

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            validate_max_results(-1)


class TestValidateUrl:
    def test_valid_https(self) -> None:
        url = "https://example.com/webhook"
        assert validate_url(url) == url

    def test_valid_http(self) -> None:
        url = "http://example.com/webhook"
        assert validate_url(url) == url

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_url("")

    def test_file_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="must use http"):
            validate_url("file:///etc/passwd")

    def test_javascript_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="must use http"):
            validate_url("javascript:alert(1)")

    def test_localhost_raises(self) -> None:
        with pytest.raises(ValueError, match="must not target localhost"):
            validate_url("https://localhost/hook")

    def test_loopback_ip_raises(self) -> None:
        with pytest.raises(ValueError, match="must not target private IP"):
            validate_url("https://127.0.0.1/hook")

    def test_10_network_raises(self) -> None:
        with pytest.raises(ValueError, match="must not target private IP"):
            validate_url("https://10.0.0.1/hook")

    def test_172_16_network_raises(self) -> None:
        with pytest.raises(ValueError, match="must not target private IP"):
            validate_url("https://172.16.0.1/hook")

    def test_192_168_network_raises(self) -> None:
        with pytest.raises(ValueError, match="must not target private IP"):
            validate_url("https://192.168.1.1/hook")

    def test_link_local_raises(self) -> None:
        with pytest.raises(ValueError, match="must not target private IP"):
            validate_url("https://169.254.1.1/hook")

    def test_no_hostname_raises(self) -> None:
        with pytest.raises(ValueError, match="must have a valid hostname"):
            validate_url("https:///path")

    def test_ipv6_loopback_raises(self) -> None:
        with pytest.raises(ValueError, match="must not target localhost"):
            validate_url("https://[::1]/hook")

    def test_172_31_network_raises(self) -> None:
        with pytest.raises(ValueError, match="must not target private IP"):
            validate_url("https://172.31.0.1/hook")


class TestValidateEnum:
    def test_valid_value(self) -> None:
        assert validate_enum("OPEN", "state", PR_STATES) == "OPEN"

    def test_case_insensitive(self) -> None:
        assert validate_enum("open", "state", PR_STATES) == "OPEN"

    def test_mixed_case(self) -> None:
        assert validate_enum("Merged", "state", PR_STATES) == "MERGED"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError, match="must be one of"):
            validate_enum("INVALID", "state", PR_STATES)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_enum("", "state", PR_STATES)

    def test_build_states(self) -> None:
        assert validate_enum("successful", "state", BUILD_STATES) == "SUCCESSFUL"


class TestValidateUrlPathSegment:
    def test_normal_segment(self) -> None:
        assert validate_url_path_segment("my-repo") == "my-repo"

    def test_encodes_special_chars(self) -> None:
        result = validate_url_path_segment("path/to")
        assert "/" not in result

    def test_encodes_spaces(self) -> None:
        result = validate_url_path_segment("my repo")
        assert " " not in result
        assert "my%20repo" == result

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_url_path_segment("")


class TestValidateFilePath:
    def test_normal_path(self) -> None:
        assert validate_file_path("src/main.py") == "src/main.py"

    def test_root_path(self) -> None:
        assert validate_file_path("README.md") == "README.md"

    def test_empty_path_allowed(self) -> None:
        assert validate_file_path("") == ""

    def test_traversal_raises(self) -> None:
        with pytest.raises(ValueError, match="must not contain.*traversal"):
            validate_file_path("../../etc/passwd")

    def test_mid_path_traversal_raises(self) -> None:
        with pytest.raises(ValueError, match="must not contain.*traversal"):
            validate_file_path("src/../../../etc/passwd")

    def test_double_dot_in_filename_allowed(self) -> None:
        assert validate_file_path("file..name.txt") == "file..name.txt"


class TestSafeErrorText:
    def test_short_text_unchanged(self) -> None:
        assert _safe_error_text("error occurred") == "error occurred"

    def test_truncation(self) -> None:
        long_text = "x" * 500
        result = _safe_error_text(long_text)
        assert len(result) == 200

    def test_custom_max_len(self) -> None:
        result = _safe_error_text("abcdefghij", max_len=5)
        assert result == "abcde"

    def test_redacts_bearer_token(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJIUz failed"
        result = _safe_error_text(text)
        assert "eyJhbGci" not in result
        assert "[REDACTED]" in result

    def test_redacts_basic_auth(self) -> None:
        text = "Authorization: Basic dXNlcjpwYXNz failed"
        result = _safe_error_text(text)
        assert "dXNlcjpwYXNz" not in result
        assert "[REDACTED]" in result
