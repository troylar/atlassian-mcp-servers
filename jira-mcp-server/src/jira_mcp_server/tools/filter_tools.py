"""MCP tools for filter management."""

from typing import Any, Dict, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.formatters import (
    _get_summary_api_fields,
    _resolve_detail,
    format_issues,
)
from jira_mcp_server.utils.text import sanitize_text

_client: Optional[JiraClient] = None
_config: Optional[JiraConfig] = None


def initialize_filter_tools(client: JiraClient, config: JiraConfig) -> None:
    global _client, _config
    _client = client
    _config = config


def jira_filter_create(
    name: str, jql: str, description: str | None = None, favourite: bool = False
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Filter tools not initialized")
    if not name or not name.strip():
        raise ValueError("Filter name cannot be empty")
    if not jql or not jql.strip():
        raise ValueError("JQL query cannot be empty")
    try:
        return _client.create_filter(
            name=sanitize_text(name),
            jql=sanitize_text(jql),
            description=sanitize_text(description) if description else description,
            favourite=favourite,
        )
    except Exception as e:
        raise ValueError(f"Filter creation failed: {str(e)}")


def jira_filter_list() -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Filter tools not initialized")
    try:
        return _client.list_filters()
    except Exception as e:
        raise ValueError(f"Filter list failed: {str(e)}")


def jira_filter_get(filter_id: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Filter tools not initialized")
    if not filter_id or not filter_id.strip():
        raise ValueError("Filter ID cannot be empty")
    try:
        return _client.get_filter(filter_id=filter_id)
    except Exception as e:
        raise ValueError(f"Get filter failed: {str(e)}")


def jira_filter_execute(
    filter_id: str, max_results: int = 50, start_at: int = 0, detail: Optional[str] = None
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Filter tools not initialized")
    resolved = _resolve_detail(detail, _config)
    if not filter_id or not filter_id.strip():
        raise ValueError("Filter ID cannot be empty")
    try:
        filter_data = _client.get_filter(filter_id=filter_id)
        jql = filter_data.get("jql")
        if not jql:
            raise ValueError("Filter does not contain a valid JQL query")
        fields_param = _get_summary_api_fields(_config) if resolved == "summary" else None
        raw = _client.search_issues(jql=jql, max_results=max_results, start_at=start_at, fields=fields_param)
        if resolved == "summary":
            return format_issues(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"Filter execution failed: {str(e)}")


def jira_filter_update(
    filter_id: str,
    name: str | None = None,
    jql: str | None = None,
    description: str | None = None,
    favourite: bool | None = None,
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Filter tools not initialized")
    if not filter_id or not filter_id.strip():
        raise ValueError("Filter ID cannot be empty")
    if name is None and jql is None and description is None and favourite is None:
        raise ValueError("At least one field must be provided to update")
    try:
        return _client.update_filter(
            filter_id=filter_id,
            name=sanitize_text(name) if name else name,
            jql=sanitize_text(jql) if jql else jql,
            description=sanitize_text(description) if description else description,
            favourite=favourite,
        )
    except Exception as e:
        raise ValueError(f"Filter update failed: {str(e)}")


def jira_filter_delete(filter_id: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Filter tools not initialized")
    if not filter_id or not filter_id.strip():
        raise ValueError("Filter ID cannot be empty")
    try:
        _client.delete_filter(filter_id=filter_id)
        return {"success": True, "message": f"Filter {filter_id} deleted successfully"}
    except Exception as e:
        raise ValueError(f"Filter deletion failed: {str(e)}")
