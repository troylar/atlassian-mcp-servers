"""MCP tools for board operations (Agile)."""

from typing import Any, Dict, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.formatters import _resolve_detail, format_board

_client: Optional[JiraClient] = None
_config: Optional[JiraConfig] = None


def initialize_board_tools(client: JiraClient, config: JiraConfig) -> None:
    global _client, _config
    _client = client
    _config = config


def jira_board_list(project_key: str | None = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Board tools not initialized")
    try:
        return _client.list_boards(project_key=project_key)
    except Exception as e:
        raise ValueError(f"List boards failed: {str(e)}")


def jira_board_get(board_id: str, detail: Optional[str] = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Board tools not initialized")
    resolved = _resolve_detail(detail, _config)
    if not board_id or not board_id.strip():
        raise ValueError("Board ID cannot be empty")
    try:
        raw = _client.get_board(board_id)
        if resolved == "summary":
            return format_board(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"Get board failed: {str(e)}")
