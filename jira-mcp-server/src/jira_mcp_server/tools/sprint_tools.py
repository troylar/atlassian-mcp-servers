"""MCP tools for sprint operations (Agile)."""

from typing import Any, Dict, Optional

from jira_mcp_server.client import JiraClient

_client: Optional[JiraClient] = None


def initialize_sprint_tools(client: JiraClient) -> None:
    global _client
    _client = client


def jira_sprint_list(board_id: str, state: str | None = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Sprint tools not initialized")
    if not board_id or not board_id.strip():
        raise ValueError("Board ID cannot be empty")
    try:
        return _client.list_sprints(board_id, state=state)
    except Exception as e:
        raise ValueError(f"List sprints failed: {str(e)}")


def jira_sprint_get(sprint_id: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Sprint tools not initialized")
    if not sprint_id or not sprint_id.strip():
        raise ValueError("Sprint ID cannot be empty")
    try:
        return _client.get_sprint(sprint_id)
    except Exception as e:
        raise ValueError(f"Get sprint failed: {str(e)}")


def jira_sprint_issues(sprint_id: str, max_results: int = 50, start_at: int = 0) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Sprint tools not initialized")
    if not sprint_id or not sprint_id.strip():
        raise ValueError("Sprint ID cannot be empty")
    try:
        return _client.get_sprint_issues(sprint_id, max_results=max_results, start_at=start_at)
    except Exception as e:
        raise ValueError(f"Get sprint issues failed: {str(e)}")
