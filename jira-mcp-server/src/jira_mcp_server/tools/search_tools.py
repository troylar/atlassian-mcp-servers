"""MCP tools for issue search."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient

_client: Optional[JiraClient] = None


def initialize_search_tools(client: JiraClient) -> None:
    global _client
    _client = client


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
        clauses.append(f"project = {project}")
    if assignee:
        if assignee == "currentUser()":
            clauses.append("assignee = currentUser()")
        else:
            clauses.append(f"assignee = {assignee}")
    if status:
        clauses.append(f'status = "{status}"')
    if priority:
        clauses.append(f'priority = "{priority}"')
    if labels:
        for label in labels:
            clauses.append(f'labels = "{label}"')
    if created_after:
        clauses.append(f'created >= "{created_after}"')
    if created_before:
        clauses.append(f'created <= "{created_before}"')
    if updated_after:
        clauses.append(f'updated >= "{updated_after}"')
    if updated_before:
        clauses.append(f'updated <= "{updated_before}"')
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
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Search tools not initialized")
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
        return _client.search_issues(jql=jql, max_results=max_results, start_at=start_at)
    except Exception as e:
        raise ValueError(f"Search failed: {str(e)}")


def jira_search_jql(
    jql: str,
    max_results: int = 50,
    start_at: int = 0,
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Search tools not initialized")
    if not jql or not jql.strip():
        raise ValueError("JQL query cannot be empty")
    try:
        return _client.search_issues(jql=jql, max_results=max_results, start_at=start_at)
    except Exception as e:
        raise ValueError(f"JQL search failed: {str(e)}")
