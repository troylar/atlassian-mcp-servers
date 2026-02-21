"""Tests for JiraConfig."""

import pytest
from pydantic import ValidationError

from jira_mcp_server.config import AuthType, JiraConfig


class TestAuthTypeAutoDetection:
    def test_pat_auth_when_only_token_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.PAT

    def test_cloud_auth_when_email_and_token_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://company.atlassian.net")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "api-token")
        monkeypatch.setenv("JIRA_MCP_EMAIL", "user@company.com")
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.CLOUD
        assert config.email == "user@company.com"

    def test_explicit_auth_type_override_pat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_EMAIL", "user@company.com")
        monkeypatch.setenv("JIRA_MCP_AUTH_TYPE", "pat")
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.PAT

    def test_explicit_auth_type_override_cloud(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://company.atlassian.net")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "api-token")
        monkeypatch.setenv("JIRA_MCP_EMAIL", "user@company.com")
        monkeypatch.setenv("JIRA_MCP_AUTH_TYPE", "cloud")
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.auth_type == AuthType.CLOUD

    def test_cloud_auth_requires_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://company.atlassian.net")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "api-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.setenv("JIRA_MCP_AUTH_TYPE", "cloud")
        with pytest.raises(ValidationError, match="JIRA_MCP_EMAIL is required"):
            JiraConfig()  # type: ignore[call-arg]


class TestUrlHandling:
    def test_trailing_slash_removed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com/")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.url == "https://jira.example.com"

    def test_multiple_trailing_slashes_removed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com///")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.url == "https://jira.example.com"

    def test_no_trailing_slash_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.url == "https://jira.example.com"


class TestDefaults:
    def test_default_cache_ttl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.cache_ttl == 3600

    def test_default_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.timeout == 30

    def test_default_verify_ssl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.verify_ssl is True

    def test_custom_cache_ttl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_CACHE_TTL", "7200")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.cache_ttl == 7200

    def test_custom_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_TIMEOUT", "60")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.timeout == 60

    def test_verify_ssl_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_VERIFY_SSL", "false")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        config = JiraConfig()  # type: ignore[call-arg]
        assert config.verify_ssl is False


class TestValidation:
    def test_cache_ttl_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_CACHE_TTL", "0")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError):
            JiraConfig()  # type: ignore[call-arg]

    def test_timeout_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_TIMEOUT", "0")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError):
            JiraConfig()  # type: ignore[call-arg]

    def test_cache_ttl_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_CACHE_TTL", "-1")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError):
            JiraConfig()  # type: ignore[call-arg]

    def test_timeout_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_TIMEOUT", "-5")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError):
            JiraConfig()  # type: ignore[call-arg]

    def test_missing_url_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JIRA_MCP_URL", raising=False)
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError):
            JiraConfig()  # type: ignore[call-arg]

    def test_missing_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.delenv("JIRA_MCP_TOKEN", raising=False)
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        with pytest.raises(ValidationError):
            JiraConfig()  # type: ignore[call-arg]
