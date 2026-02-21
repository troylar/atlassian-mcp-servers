"""MCP tools for board operations (Agile)."""

from typing import Any, Dict, Optional

from jira_mcp_server.client import JiraClient

_client: Optional[JiraClient] = None


def initialize_board_tools(client: JiraClient) -> None:
    global _client
    _client = client


def jira_board_list(project_key: str | None = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Board tools not initialized")
    try:
        return _client.list_boards(project_key=project_key)
    except Exception as e:
        raise ValueError(f"List boards failed: {str(e)}")


def jira_board_get(board_id: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Board tools not initialized")
    if not board_id or not board_id.strip():
        raise ValueError("Board ID cannot be empty")
    try:
        return _client.get_board(board_id)
    except Exception as e:
        raise ValueError(f"Get board failed: {str(e)}")
