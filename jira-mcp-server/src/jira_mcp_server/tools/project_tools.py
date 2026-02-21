"""MCP tools for project operations."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient

_client: Optional[JiraClient] = None


def initialize_project_tools(client: JiraClient) -> None:
    global _client
    _client = client


def jira_project_list() -> List[Dict[str, Any]]:
    if not _client:
        raise RuntimeError("Project tools not initialized")
    try:
        return _client.list_projects()
    except Exception as e:
        raise ValueError(f"List projects failed: {str(e)}")


def jira_project_get(project_key: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Project tools not initialized")
    if not project_key or not project_key.strip():
        raise ValueError("Project key cannot be empty")
    try:
        return _client.get_project(project_key)
    except Exception as e:
        raise ValueError(f"Get project failed: {str(e)}")


def jira_project_issue_types(project_key: str) -> List[Dict[str, Any]]:
    if not _client:
        raise RuntimeError("Project tools not initialized")
    if not project_key or not project_key.strip():
        raise ValueError("Project key cannot be empty")
    try:
        return _client.get_issue_types(project_key)
    except Exception as e:
        raise ValueError(f"Get issue types failed: {str(e)}")
