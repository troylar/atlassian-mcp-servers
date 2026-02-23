"""MCP tools for user operations."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.formatters import _resolve_detail, format_user, format_users
from jira_mcp_server.utils.text import sanitize_text

_client: Optional[JiraClient] = None
_config: Optional[JiraConfig] = None


def initialize_user_tools(client: JiraClient, config: JiraConfig) -> None:
    global _client, _config
    _client = client
    _config = config


def jira_user_search(query: str, max_results: int = 50, detail: Optional[str] = None) -> List[Dict[str, Any]]:
    if not _client:
        raise RuntimeError("User tools not initialized")
    resolved = _resolve_detail(detail, _config)
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")
    try:
        raw = _client.search_users(sanitize_text(query), max_results=max_results)
        if resolved == "summary":
            return format_users(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"User search failed: {str(e)}")


def jira_user_get(username: str, detail: Optional[str] = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("User tools not initialized")
    resolved = _resolve_detail(detail, _config)
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")
    try:
        raw = _client.get_user(username)
        if resolved == "summary":
            return format_user(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"Get user failed: {str(e)}")


def jira_user_myself(detail: Optional[str] = None) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("User tools not initialized")
    resolved = _resolve_detail(detail, _config)
    try:
        raw = _client.get_myself()
        if resolved == "summary":
            return format_user(raw, _config)
        return raw
    except Exception as e:
        raise ValueError(f"Get current user failed: {str(e)}")
