"""MCP tools for issue search."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.formatters import (
    _get_summary_api_fields,
    _resolve_detail,
    format_issues,
)
from jira_mcp_server.utils.text import escape_jql_value, sanitize_text

_client: Optional[JiraClient] = None
_config: Optional[JiraConfig] = None


def initialize_search_tools(client: JiraClient, config: JiraConfig) -> None:
    global _client, _config
    _client = client
    _config = config


def build_jql_from_criteria(
    project: Optional[str] = None,
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    labels: Optional[List[str]] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None,
) -> str:
    clauses: List[str] = []
    if project:
        clauses.append(f"project = {escape_jql_value(project)}")
    if assignee:
        if assignee == "currentUser()":
            clauses.append("assignee = currentUser()")
        else:
            clauses.append(f"assignee = {escape_jql_value(assignee)}")
    if status:
        clauses.append(f"status = {escape_jql_value(status)}")
    if priority:
        clauses.append(f"priority = {escape_jql_value(priority)}")
    if labels:
        for label in labels:
            clauses.append(f"labels = {escape_jql_value(label)}")
    if created_after:
        clauses.append(f"created >= {escape_jql_value(created_after)}")
    if created_before:
        clauses.append(f"created <= {escape_jql_value(created_before)}")
    if updated_after:
        clauses.append(f"updated >= {escape_jql_value(updated_after)}")
    if updated_before:
        clauses.append(f"updated <= {escape_jql_value(updated_before)}")
    return " AND ".join(clauses) if clauses else ""


def jira_search_issues(
    project: Optional[str] = None,
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    labels: Optional[List[str]] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None,
    max_results: int = 50,
    start_at: int = 0,
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Search tools not initialized")
    resolved = _resolve_detail(detail, _config)
    jql = build_jql_from_criteria(
        project=project,
        assignee=assignee,
        status=status,
        priority=priority,
        labels=labels,
        created_after=created_after,
        created_before=created_before,
        updated_after=updated_after,
        updated_before=updated_before,
    )
    if not jql:
        raise ValueError("At least one search criterion must be provided")
    try:
        fields_param = _get_summary_api_fields(_config) if resolved == "summary" else None
        raw = _client.search_issues(
            jql=jql, max_results=max_results, start_at=start_at, fields=fields_param
        )
        if resolved == "summary":
            return format_issues(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"Search failed: {str(e)}")


def jira_search_jql(
    jql: str,
    max_results: int = 50,
    start_at: int = 0,
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Search tools not initialized")
    resolved = _resolve_detail(detail, _config)
    if not jql or not jql.strip():
        raise ValueError("JQL query cannot be empty")
    try:
        fields_param = _get_summary_api_fields(_config) if resolved == "summary" else None
        raw = _client.search_issues(
            jql=sanitize_text(jql), max_results=max_results, start_at=start_at, fields=fields_param
        )
        if resolved == "summary":
            return format_issues(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"JQL search failed: {str(e)}")
