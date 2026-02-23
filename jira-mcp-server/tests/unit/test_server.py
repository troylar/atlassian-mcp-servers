"""Tests for server.py non-tool functions."""

from unittest.mock import MagicMock, patch

import pytest

from jira_mcp_server.server import _jira_health_check


class TestJiraHealthCheck:
    def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        with patch("jira_mcp_server.server.JiraClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.health_check.return_value = {"connected": True, "server_version": "9.0.0"}
            mock_cls.return_value = mock_client
            result = _jira_health_check()
        assert result["connected"] is True

    def test_exception_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        with patch("jira_mcp_server.server.JiraClient") as mock_cls:
            mock_cls.side_effect = ValueError("connection error")
            result = _jira_health_check()
        assert result["connected"] is False
        assert "connection error" in result["error"]

    def test_config_error_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JIRA_MCP_URL", raising=False)
        monkeypatch.delenv("JIRA_MCP_TOKEN", raising=False)
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        result = _jira_health_check()
        assert result["connected"] is False


class TestMain:
    def test_main_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        from jira_mcp_server.server import main

        with (
            patch("jira_mcp_server.server.JiraClient"),
            patch("jira_mcp_server.server.initialize_issue_tools"),
            patch("jira_mcp_server.server.initialize_search_tools"),
            patch("jira_mcp_server.server.initialize_filter_tools"),
            patch("jira_mcp_server.server.initialize_workflow_tools"),
            patch("jira_mcp_server.server.initialize_comment_tools"),
            patch("jira_mcp_server.server.initialize_project_tools"),
            patch("jira_mcp_server.server.initialize_board_tools"),
            patch("jira_mcp_server.server.initialize_sprint_tools"),
            patch("jira_mcp_server.server.initialize_user_tools"),
            patch("jira_mcp_server.server.initialize_attachment_tools"),
            patch("jira_mcp_server.server.mcp") as mock_mcp,
        ):
            main()
            mock_mcp.run.assert_called_once()

    def test_main_ssl_disabled_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("JIRA_MCP_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_MCP_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_MCP_VERIFY_SSL", "false")
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        from jira_mcp_server.server import main

        with (
            caplog.at_level("WARNING", logger="jira_mcp_server.server"),
            patch("jira_mcp_server.server.JiraClient"),
            patch("jira_mcp_server.server.initialize_issue_tools"),
            patch("jira_mcp_server.server.initialize_search_tools"),
            patch("jira_mcp_server.server.initialize_filter_tools"),
            patch("jira_mcp_server.server.initialize_workflow_tools"),
            patch("jira_mcp_server.server.initialize_comment_tools"),
            patch("jira_mcp_server.server.initialize_project_tools"),
            patch("jira_mcp_server.server.initialize_board_tools"),
            patch("jira_mcp_server.server.initialize_sprint_tools"),
            patch("jira_mcp_server.server.initialize_user_tools"),
            patch("jira_mcp_server.server.initialize_attachment_tools"),
            patch("jira_mcp_server.server.mcp"),
        ):
            main()
        assert "DISABLED" in caplog.text

    def test_main_config_error_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JIRA_MCP_URL", raising=False)
        monkeypatch.delenv("JIRA_MCP_TOKEN", raising=False)
        monkeypatch.delenv("JIRA_MCP_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_MCP_AUTH_TYPE", raising=False)
        from jira_mcp_server.server import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
