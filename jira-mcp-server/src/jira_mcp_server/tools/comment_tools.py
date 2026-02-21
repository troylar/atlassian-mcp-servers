"""MCP tools for issue comments."""

from typing import Any, Dict, Optional

from jira_mcp_server.client import JiraClient

_client: Optional[JiraClient] = None


def initialize_comment_tools(client: JiraClient) -> None:
    global _client
    _client = client


def jira_comment_add(issue_key: str, body: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Comment tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    if not body or not body.strip():
        raise ValueError("Comment body cannot be empty")
    try:
        return _client.add_comment(issue_key=issue_key, body=body)
    except Exception as e:
        raise ValueError(f"Add comment failed: {str(e)}")


def jira_comment_list(issue_key: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Comment tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    try:
        return _client.list_comments(issue_key=issue_key)
    except Exception as e:
        raise ValueError(f"List comments failed: {str(e)}")


def jira_comment_update(issue_key: str, comment_id: str, body: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Comment tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    if not comment_id or not comment_id.strip():
        raise ValueError("Comment ID cannot be empty")
    if not body or not body.strip():
        raise ValueError("Comment body cannot be empty")
    try:
        return _client.update_comment(issue_key=issue_key, comment_id=comment_id, body=body)
    except Exception as e:
        raise ValueError(f"Update comment failed: {str(e)}")


def jira_comment_delete(issue_key: str, comment_id: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Comment tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    if not comment_id or not comment_id.strip():
        raise ValueError("Comment ID cannot be empty")
    try:
        _client.delete_comment(issue_key=issue_key, comment_id=comment_id)
        return {
            "success": True,
            "message": f"Comment {comment_id} deleted successfully",
            "issue_key": issue_key,
            "comment_id": comment_id,
        }
    except Exception as e:
        raise ValueError(f"Delete comment failed: {str(e)}")
