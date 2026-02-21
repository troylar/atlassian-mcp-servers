"""MCP tools for attachment operations."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient

_client: Optional[JiraClient] = None


def initialize_attachment_tools(client: JiraClient) -> None:
    global _client
    _client = client


def jira_attachment_add(issue_key: str, file_path: str, filename: str | None = None) -> List[Dict[str, Any]]:
    if not _client:
        raise RuntimeError("Attachment tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    if not file_path or not file_path.strip():
        raise ValueError("File path cannot be empty")
    try:
        return _client.add_attachment(issue_key, file_path, filename=filename)
    except Exception as e:
        raise ValueError(f"Add attachment failed: {str(e)}")


def jira_attachment_get(attachment_id: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Attachment tools not initialized")
    if not attachment_id or not attachment_id.strip():
        raise ValueError("Attachment ID cannot be empty")
    try:
        return _client.get_attachment(attachment_id)
    except Exception as e:
        raise ValueError(f"Get attachment failed: {str(e)}")


def jira_attachment_delete(attachment_id: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Attachment tools not initialized")
    if not attachment_id or not attachment_id.strip():
        raise ValueError("Attachment ID cannot be empty")
    try:
        _client.delete_attachment(attachment_id)
        return {"success": True, "message": f"Attachment {attachment_id} deleted successfully"}
    except Exception as e:
        raise ValueError(f"Delete attachment failed: {str(e)}")
