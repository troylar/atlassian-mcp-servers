"""MCP tools for sprint operations (Agile)."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.formatters import (
    _get_summary_api_fields,
    _resolve_detail,
    format_issues,
    format_sprint,
)
from jira_mcp_server.validators import validate_issue_key, validate_numeric_id

_client: Optional[JiraClient] = None
_config: Optional[JiraConfig] = None


def initialize_sprint_tools(client: JiraClient, config: JiraConfig) -> None:
    global _client, _config
    _client = client
    _config = config


def jira_sprint_list(board_id: str, state: str | None = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Sprint tools not initialized")
    if not board_id or not board_id.strip():
        raise ValueError("Board ID cannot be empty")
    try:
        return _client.list_sprints(board_id, state=state)
    except Exception as e:
        raise ValueError(f"List sprints failed: {str(e)}")


def jira_sprint_get(sprint_id: str, detail: Optional[str] = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Sprint tools not initialized")
    resolved = _resolve_detail(detail, _config)
    if not sprint_id or not sprint_id.strip():
        raise ValueError("Sprint ID cannot be empty")
    try:
        raw = _client.get_sprint(sprint_id)
        if resolved == "summary":
            return format_sprint(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"Get sprint failed: {str(e)}")


def jira_sprint_issues(
    sprint_id: str, max_results: int = 50, start_at: int = 0, detail: Optional[str] = None
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Sprint tools not initialized")
    resolved = _resolve_detail(detail, _config)
    if not sprint_id or not sprint_id.strip():
        raise ValueError("Sprint ID cannot be empty")
    try:
        fields_param = _get_summary_api_fields(_config) if resolved == "summary" else None
        raw = _client.get_sprint_issues(
            sprint_id, max_results=max_results, start_at=start_at, fields=fields_param
        )
        if resolved == "summary":
            return format_issues(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"Get sprint issues failed: {str(e)}")


def jira_sprint_add_issues(sprint_id: str, issue_keys: List[str]) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Sprint tools not initialized")
    validate_numeric_id(sprint_id, name="sprint_id")
    if not issue_keys:
        raise ValueError("issue_keys must not be empty")
    validated_keys = [validate_issue_key(k) for k in issue_keys]
    try:
        return _client.add_issues_to_sprint(sprint_id, validated_keys)
    except Exception as e:
        raise ValueError(f"Add issues to sprint failed: {str(e)}")


def jira_sprint_remove_issues(issue_keys: List[str]) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Sprint tools not initialized")
    if not issue_keys:
        raise ValueError("issue_keys must not be empty")
    validated_keys = [validate_issue_key(k) for k in issue_keys]
    try:
        return _client.remove_issues_from_sprint(validated_keys)
    except Exception as e:
        raise ValueError(f"Remove issues from sprint failed: {str(e)}")
