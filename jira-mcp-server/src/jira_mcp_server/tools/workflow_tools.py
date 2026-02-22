"""MCP tools for workflow transitions."""

from typing import Any, Dict, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.utils.text import sanitize_value

_client: Optional[JiraClient] = None


def initialize_workflow_tools(client: JiraClient) -> None:
    global _client
    _client = client


def jira_workflow_get_transitions(issue_key: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Workflow tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    try:
        result = _client.get_transitions(issue_key=issue_key)
        transitions = result.get("transitions", [])
        return {
            "issue_key": issue_key,
            "transitions": [
                {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "to_status": t.get("to", {}).get("name"),
                    "has_screen": t.get("hasScreen", False),
                    "fields": list(t.get("fields", {}).keys()) if t.get("fields") else [],
                }
                for t in transitions
            ],
        }
    except Exception as e:
        raise ValueError(f"Get transitions failed: {str(e)}")


def jira_workflow_transition(
    issue_key: str, transition_id: str, fields: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Workflow tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    if not transition_id or not transition_id.strip():
        raise ValueError("Transition ID cannot be empty")
    try:
        sanitized_fields = sanitize_value(fields) if fields else fields
        _client.transition_issue(issue_key=issue_key, transition_id=transition_id, fields=sanitized_fields)
        return {
            "success": True,
            "message": f"Issue {issue_key} transitioned successfully",
            "issue_key": issue_key,
            "transition_id": transition_id,
        }
    except Exception as e:
        raise ValueError(f"Transition failed: {str(e)}")
