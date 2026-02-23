"""Tests for ConfluenceConfig."""

import pytest

from confluence_mcp_server.config import AuthType, ConfluenceConfig


class TestAuthTypeEnum:
    def test_pat_value(self) -> None:
        assert AuthType.PAT.value == "pat"

    def test_cloud_value(self) -> None:
        assert AuthType.CLOUD.value == "cloud"

    def test_is_str_enum(self) -> None:
        assert isinstance(AuthType.PAT, str)
        assert isinstance(AuthType.CLOUD, str)


class TestConfluenceConfigPATAutoDetect:
    def test_only_token_set_defaults_to_pat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.PAT
        assert config.email is None

    def test_token_only_no_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://dc.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "my-pat")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.PAT


class TestConfluenceConfigCloudAutoDetect:
    def test_email_and_token_set_defaults_to_cloud(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://company.atlassian.net")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "api-token")
        monkeypatch.setenv("CONFLUENCE_MCP_EMAIL", "user@company.com")
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.CLOUD
        assert config.email == "user@company.com"


class TestConfluenceConfigExplicitAuthType:
    def test_explicit_pat_with_email_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.setenv("CONFLUENCE_MCP_EMAIL", "user@example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_AUTH_TYPE", "pat")

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.PAT

    def test_explicit_cloud_with_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://company.atlassian.net")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "api-token")
        monkeypatch.setenv("CONFLUENCE_MCP_EMAIL", "user@company.com")
        monkeypatch.setenv("CONFLUENCE_MCP_AUTH_TYPE", "cloud")

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.CLOUD

    def test_explicit_cloud_without_email_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://company.atlassian.net")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "api-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.setenv("CONFLUENCE_MCP_AUTH_TYPE", "cloud")

        with pytest.raises(ValueError, match="CONFLUENCE_MCP_EMAIL is required"):
            ConfluenceConfig()  # type: ignore[call-arg]


class TestConfluenceConfigCloudRequiresEmail:
    def test_auto_cloud_without_email_impossible(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no email is set and no explicit auth_type, auto-detect picks PAT, not cloud."""
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://company.atlassian.net")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "api-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.PAT


class TestConfluenceConfigURLTrailingSlash:
    def test_trailing_slash_removed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com/")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.url == "https://confluence.example.com"

    def test_multiple_trailing_slashes_removed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com///")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.url == "https://confluence.example.com"

    def test_no_trailing_slash_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.url == "https://confluence.example.com"


class TestConfluenceConfigDefaults:
    def test_default_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.timeout == 30

    def test_default_verify_ssl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.verify_ssl is True

    def test_default_email_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.email is None

    def test_custom_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.setenv("CONFLUENCE_MCP_TIMEOUT", "60")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.timeout == 60

    def test_custom_verify_ssl_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.setenv("CONFLUENCE_MCP_VERIFY_SSL", "false")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.verify_ssl is False

    def test_env_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)

        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.url == "https://confluence.example.com"
        assert config.token == "test-token"


class TestLogLevel:
    def test_default_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_LOG_LEVEL", raising=False)
        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.log_level == "WARNING"

    def test_custom_log_level_debug(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.setenv("CONFLUENCE_MCP_LOG_LEVEL", "DEBUG")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)
        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.log_level == "DEBUG"

    def test_custom_log_level_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.setenv("CONFLUENCE_MCP_LOG_LEVEL", "INFO")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)
        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.log_level == "INFO"

    def test_custom_log_level_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.setenv("CONFLUENCE_MCP_LOG_LEVEL", "ERROR")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)
        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.log_level == "ERROR"

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.setenv("CONFLUENCE_MCP_LOG_LEVEL", "debug")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)
        config = ConfluenceConfig()  # type: ignore[call-arg]
        assert config.log_level == "DEBUG"

    def test_invalid_log_level_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_MCP_URL", "https://confluence.example.com")
        monkeypatch.setenv("CONFLUENCE_MCP_TOKEN", "test-token")
        monkeypatch.setenv("CONFLUENCE_MCP_LOG_LEVEL", "VERBOSE")
        monkeypatch.delenv("CONFLUENCE_MCP_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_MCP_AUTH_TYPE", raising=False)
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Invalid log_level"):
            ConfluenceConfig()  # type: ignore[call-arg]
