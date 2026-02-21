"""MCP tools for user operations."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient

_client: Optional[JiraClient] = None


def initialize_user_tools(client: JiraClient) -> None:
    global _client
    _client = client


def jira_user_search(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    if not _client:
        raise RuntimeError("User tools not initialized")
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")
    try:
        return _client.search_users(query, max_results=max_results)
    except Exception as e:
        raise ValueError(f"User search failed: {str(e)}")


def jira_user_get(username: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("User tools not initialized")
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")
    try:
        return _client.get_user(username)
    except Exception as e:
        raise ValueError(f"Get user failed: {str(e)}")


def jira_user_myself() -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("User tools not initialized")
    try:
        return _client.get_myself()
    except Exception as e:
        raise ValueError(f"Get current user failed: {str(e)}")
