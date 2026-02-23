"""MCP tools for issue worklogs (time tracking)."""

from typing import Any, Dict, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig

_client: Optional[JiraClient] = None
_config: Optional[JiraConfig] = None


def initialize_worklog_tools(client: JiraClient, config: JiraConfig) -> None:
    global _client, _config
    _client = client
    _config = config


def jira_worklog_add(
    issue_key: str,
    time_spent: str,
    comment: Optional[str] = None,
    started: Optional[str] = None,
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Worklog tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    if not time_spent or not time_spent.strip():
        raise ValueError("Time spent cannot be empty")
    try:
        return _client.add_worklog(
            issue_key=issue_key,
            time_spent=time_spent,
            comment=comment,
            started=started,
        )
    except Exception as e:
        raise ValueError(f"Add worklog failed: {str(e)}")


def jira_worklog_list(issue_key: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Worklog tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    try:
        return _client.list_worklogs(issue_key=issue_key)
    except Exception as e:
        raise ValueError(f"List worklogs failed: {str(e)}")


def jira_worklog_delete(issue_key: str, worklog_id: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Worklog tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    if not worklog_id or not worklog_id.strip():
        raise ValueError("Worklog ID cannot be empty")
    try:
        _client.delete_worklog(issue_key=issue_key, worklog_id=worklog_id)
        return {
            "success": True,
            "message": f"Worklog {worklog_id} deleted successfully",
            "issue_key": issue_key,
            "worklog_id": worklog_id,
        }
    except Exception as e:
        raise ValueError(f"Delete worklog failed: {str(e)}")
