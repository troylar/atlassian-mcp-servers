"""Tests for BitbucketConfig."""

import pytest
from pydantic import ValidationError

from bitbucket_mcp_server.config import AuthType, BitbucketConfig


class TestAuthTypeEnum:
    def test_pat_value(self) -> None:
        assert AuthType.PAT.value == "pat"

    def test_cloud_value(self) -> None:
        assert AuthType.CLOUD.value == "cloud"

    def test_is_str_enum(self) -> None:
        assert isinstance(AuthType.PAT, str)
        assert isinstance(AuthType.CLOUD, str)


class TestBitbucketConfigPATAutoDetect:
    def test_pat_auto_detected_when_only_token_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.PAT

    def test_email_none_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.email is None


class TestBitbucketConfigCloudAutoDetect:
    def test_cloud_auto_detected_when_email_and_token_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.org")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "app-password")
        monkeypatch.setenv("BITBUCKET_MCP_EMAIL", "user@example.com")
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.CLOUD

    def test_email_stored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.org")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "app-password")
        monkeypatch.setenv("BITBUCKET_MCP_EMAIL", "user@example.com")
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.email == "user@example.com"


class TestBitbucketConfigExplicitAuthType:
    def test_explicit_pat_overrides_auto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.setenv("BITBUCKET_MCP_AUTH_TYPE", "pat")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.PAT

    def test_explicit_cloud_with_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.org")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "app-password")
        monkeypatch.setenv("BITBUCKET_MCP_EMAIL", "user@example.com")
        monkeypatch.setenv("BITBUCKET_MCP_AUTH_TYPE", "cloud")
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.CLOUD

    def test_explicit_cloud_without_email_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.org")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "app-password")
        monkeypatch.setenv("BITBUCKET_MCP_AUTH_TYPE", "cloud")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        with pytest.raises(ValidationError, match="BITBUCKET_MCP_EMAIL is required"):
            BitbucketConfig()  # type: ignore[call-arg]


class TestBitbucketConfigURLValidation:
    def test_trailing_slash_removed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com/")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.url == "https://bitbucket.example.com"

    def test_multiple_trailing_slashes_removed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com///")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.url == "https://bitbucket.example.com"

    def test_no_trailing_slash_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.url == "https://bitbucket.example.com"


class TestBitbucketConfigDefaults:
    def test_default_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.timeout == 30

    def test_default_verify_ssl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.verify_ssl is True

    def test_default_workspace_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.workspace is None

    def test_custom_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.setenv("BITBUCKET_MCP_TIMEOUT", "60")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.timeout == 60

    def test_verify_ssl_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.setenv("BITBUCKET_MCP_VERIFY_SSL", "false")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.verify_ssl is False


class TestBitbucketConfigWorkspace:
    def test_workspace_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.org")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "app-password")
        monkeypatch.setenv("BITBUCKET_MCP_EMAIL", "user@example.com")
        monkeypatch.setenv("BITBUCKET_MCP_WORKSPACE", "my-workspace")
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.workspace == "my-workspace"


class TestBitbucketConfigMissingRequired:
    def test_missing_url_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BITBUCKET_MCP_URL", raising=False)
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError):
            BitbucketConfig()  # type: ignore[call-arg]

    def test_missing_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.delenv("BITBUCKET_MCP_TOKEN", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError):
            BitbucketConfig()  # type: ignore[call-arg]


class TestLogLevel:
    def test_default_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_LOG_LEVEL", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.log_level == "WARNING"

    def test_custom_log_level_debug(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.setenv("BITBUCKET_MCP_LOG_LEVEL", "DEBUG")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.log_level == "DEBUG"

    def test_custom_log_level_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.setenv("BITBUCKET_MCP_LOG_LEVEL", "INFO")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.log_level == "INFO"

    def test_custom_log_level_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.setenv("BITBUCKET_MCP_LOG_LEVEL", "ERROR")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.log_level == "ERROR"

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.setenv("BITBUCKET_MCP_LOG_LEVEL", "debug")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        config = BitbucketConfig()  # type: ignore[call-arg]
        assert config.log_level == "DEBUG"

    def test_invalid_log_level_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BITBUCKET_MCP_URL", "https://bitbucket.example.com")
        monkeypatch.setenv("BITBUCKET_MCP_TOKEN", "test-token")
        monkeypatch.setenv("BITBUCKET_MCP_LOG_LEVEL", "VERBOSE")
        monkeypatch.delenv("BITBUCKET_MCP_EMAIL", raising=False)
        monkeypatch.delenv("BITBUCKET_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError, match="Invalid log_level"):
            BitbucketConfig()  # type: ignore[call-arg]
