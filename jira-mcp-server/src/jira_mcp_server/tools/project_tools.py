"""MCP tools for project operations."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.formatters import (
    _resolve_detail,
    format_project,
    format_projects,
)

_client: Optional[JiraClient] = None
_config: Optional[JiraConfig] = None


def initialize_project_tools(client: JiraClient, config: JiraConfig) -> None:
    global _client, _config
    _client = client
    _config = config


def jira_project_list(detail: Optional[str] = None) -> List[Dict[str, Any]]:
    if not _client:
        raise RuntimeError("Project tools not initialized")
    resolved = _resolve_detail(detail, _config)
    try:
        raw = _client.list_projects()
        if resolved == "summary":
            return format_projects(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"List projects failed: {str(e)}")


def jira_project_get(project_key: str, detail: Optional[str] = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Project tools not initialized")
    resolved = _resolve_detail(detail, _config)
    if not project_key or not project_key.strip():
        raise ValueError("Project key cannot be empty")
    try:
        raw = _client.get_project(project_key)
        if resolved == "summary":
            return format_project(raw, _config)
        return raw
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
