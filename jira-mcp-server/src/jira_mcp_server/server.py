"""FastMCP 3 server entry point for Jira MCP Server."""

import logging
import sys
from typing import Any, Dict, List

from fastmcp import FastMCP

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.tools.attachment_tools import (
    initialize_attachment_tools,
)
from jira_mcp_server.tools.attachment_tools import (
    jira_attachment_add as _impl_attachment_add,
)
from jira_mcp_server.tools.attachment_tools import (
    jira_attachment_delete as _impl_attachment_delete,
)
from jira_mcp_server.tools.attachment_tools import (
    jira_attachment_get as _impl_attachment_get,
)
from jira_mcp_server.tools.board_tools import (
    initialize_board_tools,
)
from jira_mcp_server.tools.board_tools import (
    jira_board_get as _impl_board_get,
)
from jira_mcp_server.tools.board_tools import (
    jira_board_list as _impl_board_list,
)
from jira_mcp_server.tools.comment_tools import (
    initialize_comment_tools,
)
from jira_mcp_server.tools.comment_tools import (
    jira_comment_add as _impl_comment_add,
)
from jira_mcp_server.tools.comment_tools import (
    jira_comment_delete as _impl_comment_delete,
)
from jira_mcp_server.tools.comment_tools import (
    jira_comment_list as _impl_comment_list,
)
from jira_mcp_server.tools.comment_tools import (
    jira_comment_update as _impl_comment_update,
)
from jira_mcp_server.tools.filter_tools import (
    initialize_filter_tools,
)
from jira_mcp_server.tools.filter_tools import (
    jira_filter_create as _impl_filter_create,
)
from jira_mcp_server.tools.filter_tools import (
    jira_filter_delete as _impl_filter_delete,
)
from jira_mcp_server.tools.filter_tools import (
    jira_filter_execute as _impl_filter_execute,
)
from jira_mcp_server.tools.filter_tools import (
    jira_filter_get as _impl_filter_get,
)
from jira_mcp_server.tools.filter_tools import (
    jira_filter_list as _impl_filter_list,
)
from jira_mcp_server.tools.filter_tools import (
    jira_filter_update as _impl_filter_update,
)
from jira_mcp_server.tools.issue_tools import (
    _get_field_schema,
    initialize_issue_tools,
)
from jira_mcp_server.tools.issue_tools import (
    jira_issue_create as _impl_issue_create,
)
from jira_mcp_server.tools.issue_tools import (
    jira_issue_delete as _impl_issue_delete,
)
from jira_mcp_server.tools.issue_tools import (
    jira_issue_get as _impl_issue_get,
)
from jira_mcp_server.tools.issue_tools import (
    jira_issue_link as _impl_issue_link,
)
from jira_mcp_server.tools.issue_tools import (
    jira_issue_update as _impl_issue_update,
)
from jira_mcp_server.tools.project_tools import (
    initialize_project_tools,
)
from jira_mcp_server.tools.project_tools import (
    jira_project_get as _impl_project_get,
)
from jira_mcp_server.tools.project_tools import (
    jira_project_issue_types as _impl_project_issue_types,
)
from jira_mcp_server.tools.project_tools import (
    jira_project_list as _impl_project_list,
)
from jira_mcp_server.tools.search_tools import (
    initialize_search_tools,
)
from jira_mcp_server.tools.search_tools import (
    jira_search_issues as _impl_search_issues,
)
from jira_mcp_server.tools.search_tools import (
    jira_search_jql as _impl_search_jql,
)
from jira_mcp_server.tools.sprint_tools import (
    initialize_sprint_tools,
)
from jira_mcp_server.tools.sprint_tools import (
    jira_sprint_add_issues as _impl_sprint_add_issues,
)
from jira_mcp_server.tools.sprint_tools import (
    jira_sprint_get as _impl_sprint_get,
)
from jira_mcp_server.tools.sprint_tools import (
    jira_sprint_issues as _impl_sprint_issues,
)
from jira_mcp_server.tools.sprint_tools import (
    jira_sprint_list as _impl_sprint_list,
)
from jira_mcp_server.tools.sprint_tools import (
    jira_sprint_remove_issues as _impl_sprint_remove_issues,
)
from jira_mcp_server.tools.user_tools import (
    initialize_user_tools,
)
from jira_mcp_server.tools.user_tools import (
    jira_user_get as _impl_user_get,
)
from jira_mcp_server.tools.user_tools import (
    jira_user_myself as _impl_user_myself,
)
from jira_mcp_server.tools.user_tools import (
    jira_user_search as _impl_user_search,
)
from jira_mcp_server.tools.workflow_tools import (
    initialize_workflow_tools,
)
from jira_mcp_server.tools.workflow_tools import (
    jira_workflow_get_transitions as _impl_workflow_get_transitions,
)
from jira_mcp_server.tools.workflow_tools import (
    jira_workflow_transition as _impl_workflow_transition,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("jira-mcp-server")

_client: JiraClient | None = None


def _get_client() -> JiraClient:  # pragma: no cover
    if _client is None:  # pragma: no cover
        raise RuntimeError("Jira client not initialized — server not started")  # pragma: no cover
    return _client  # pragma: no cover


# --- Health Check ---


def _jira_health_check() -> Dict[str, Any]:
    try:
        config = JiraConfig()  # type: ignore[call-arg]
        client = JiraClient(config)
        return client.health_check()
    except Exception as e:
        return {"connected": False, "error": str(e)}


@mcp.tool()
def jira_health_check() -> Dict[str, Any]:  # pragma: no cover
    """Verify connectivity to Jira instance and validate authentication."""
    return _jira_health_check()  # pragma: no cover


# --- Issue Tools ---


@mcp.tool()
def jira_issue_create(
    project: str,
    summary: str,
    issue_type: str = "Task",
    description: str = "",
    priority: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
    due_date: str | None = None,
    custom_fields: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Create a new Jira issue with automatic custom field validation.

    Args:
        project: Project key (e.g., "PROJ")
        summary: Issue title/summary (1-255 characters)
        issue_type: Type of issue (Task, Bug, Story, etc.)
        description: Detailed issue description
        priority: Issue priority
        assignee: Username or user ID to assign
        labels: List of labels
        due_date: Due date in ISO format (YYYY-MM-DD)
        custom_fields: Additional custom fields as key-value pairs
    """
    kwargs = {}  # pragma: no cover
    if custom_fields:  # pragma: no cover
        kwargs.update(custom_fields)  # pragma: no cover
    return _impl_issue_create(  # pragma: no cover
        project=project,
        summary=summary,
        issue_type=issue_type,
        description=description,
        priority=priority,
        assignee=assignee,
        labels=labels or [],
        due_date=due_date,
        **kwargs,
    )


@mcp.tool()
def jira_issue_update(
    issue_key: str,
    summary: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
    due_date: str | None = None,
    custom_fields: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Update an existing Jira issue. Only provided fields are updated.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        summary: New issue summary
        description: New issue description
        priority: New priority
        assignee: New assignee
        labels: Replace existing labels
        due_date: New due date
        custom_fields: Custom fields to update
    """
    kwargs = {}  # pragma: no cover
    if custom_fields:  # pragma: no cover
        kwargs.update(custom_fields)  # pragma: no cover
    return _impl_issue_update(  # pragma: no cover
        issue_key=issue_key,
        summary=summary,
        description=description,
        priority=priority,
        assignee=assignee,
        labels=labels,
        due_date=due_date,
        **kwargs,
    )


@mcp.tool()
def jira_issue_get(issue_key: str, detail: str | None = None) -> Dict[str, Any]:
    """Retrieve a Jira issue. Returns summary by default; use detail='full' for all fields.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_issue_get(issue_key=issue_key, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_issue_delete(issue_key: str, delete_subtasks: bool = False) -> Dict[str, Any]:
    """Delete a Jira issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        delete_subtasks: Whether to also delete subtasks (default: False)
    """
    return _impl_issue_delete(issue_key=issue_key, delete_subtasks=delete_subtasks)  # pragma: no cover


@mcp.tool()
def jira_issue_link(link_type: str, inward_issue: str, outward_issue: str) -> Dict[str, Any]:
    """Link two Jira issues together.

    Args:
        link_type: Link type name (e.g., "Blocks", "Duplicate", "Relates")
        inward_issue: Inward issue key (e.g., "PROJ-123")
        outward_issue: Outward issue key (e.g., "PROJ-456")
    """
    return _impl_issue_link(  # pragma: no cover
        link_type=link_type, inward_issue=inward_issue, outward_issue=outward_issue
    )


@mcp.tool()
def jira_project_get_schema(project: str, issue_type: str = "Task") -> Dict[str, Any]:
    """Get field schema for a project and issue type for debugging.

    Args:
        project: Project key (e.g., "PROJ")
        issue_type: Issue type name (default: "Task")
    """
    try:  # pragma: no cover
        schemas = _get_field_schema(project, issue_type)  # pragma: no cover
        return {  # pragma: no cover
            "project": project,
            "issue_type": issue_type,
            "fields": [
                {
                    "key": schema.key,
                    "name": schema.name,
                    "type": schema.type.value,
                    "required": schema.required,
                    "custom": schema.custom,
                    "allowed_values": schema.allowed_values,
                }
                for schema in schemas
            ],
        }
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}  # pragma: no cover


# --- Search Tools ---


@mcp.tool()
def jira_search_issues(
    project: str | None = None,
    assignee: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    updated_after: str | None = None,
    updated_before: str | None = None,
    max_results: int = 50,
    start_at: int = 0,
    detail: str | None = None,
) -> Dict[str, Any]:
    """Search for Jira issues using multiple criteria. At least one criterion required.

    Args:
        project: Project key (e.g., "PROJ")
        assignee: Assignee username or "currentUser()"
        status: Status name (e.g., "Open", "In Progress")
        priority: Priority name (e.g., "High", "Critical")
        labels: List of label names
        created_after: Created after date (YYYY-MM-DD)
        created_before: Created before date (YYYY-MM-DD)
        updated_after: Updated after date (YYYY-MM-DD)
        updated_before: Updated before date (YYYY-MM-DD)
        max_results: Maximum results (default: 50)
        start_at: Starting offset for pagination
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_search_issues(  # pragma: no cover
        project=project, assignee=assignee, status=status, priority=priority,
        labels=labels, created_after=created_after, created_before=created_before,
        updated_after=updated_after, updated_before=updated_before,
        max_results=max_results, start_at=start_at, detail=detail,
    )


@mcp.tool()
def jira_search_jql(
    jql: str, max_results: int = 50, start_at: int = 0, detail: str | None = None
) -> Dict[str, Any]:
    """Execute a JQL query directly. Supports all JQL operators and ORDER BY.

    Args:
        jql: JQL query string
        max_results: Maximum results (default: 50)
        start_at: Starting offset for pagination
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_search_jql(jql=jql, max_results=max_results, start_at=start_at, detail=detail)  # pragma: no cover


# --- Filter Tools ---


@mcp.tool()
def jira_filter_create(
    name: str, jql: str, description: str | None = None, favourite: bool = False
) -> Dict[str, Any]:
    """Create a new saved filter for reusing complex search queries.

    Args:
        name: Filter name
        jql: JQL query string
        description: Optional filter description
        favourite: Whether to mark as favorite
    """
    return _impl_filter_create(name=name, jql=jql, description=description, favourite=favourite)  # pragma: no cover


@mcp.tool()
def jira_filter_list() -> Dict[str, Any]:
    """List all accessible filters."""
    return _impl_filter_list()  # pragma: no cover


@mcp.tool()
def jira_filter_get(filter_id: str) -> Dict[str, Any]:
    """Get complete filter details by ID.

    Args:
        filter_id: Filter ID
    """
    return _impl_filter_get(filter_id=filter_id)  # pragma: no cover


@mcp.tool()
def jira_filter_execute(
    filter_id: str, max_results: int = 50, start_at: int = 0, detail: str | None = None
) -> Dict[str, Any]:
    """Execute a saved filter and return matching issues.

    Args:
        filter_id: Filter ID
        max_results: Maximum results (default: 50)
        start_at: Starting offset for pagination
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_filter_execute(  # pragma: no cover
        filter_id=filter_id, max_results=max_results, start_at=start_at, detail=detail
    )


@mcp.tool()
def jira_filter_update(
    filter_id: str,
    name: str | None = None,
    jql: str | None = None,
    description: str | None = None,
    favourite: bool | None = None,
) -> Dict[str, Any]:
    """Update an existing filter. Only provided fields are updated.

    Args:
        filter_id: Filter ID
        name: New filter name
        jql: New JQL query
        description: New description
        favourite: Whether to mark as favorite
    """
    return _impl_filter_update(  # pragma: no cover
        filter_id=filter_id, name=name, jql=jql, description=description, favourite=favourite
    )


@mcp.tool()
def jira_filter_delete(filter_id: str) -> Dict[str, Any]:
    """Delete a filter. Only the filter owner can delete it.

    Args:
        filter_id: Filter ID
    """
    return _impl_filter_delete(filter_id=filter_id)  # pragma: no cover


# --- Workflow Tools ---


@mcp.tool()
def jira_workflow_get_transitions(issue_key: str) -> Dict[str, Any]:
    """Get available workflow transitions for an issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
    """
    return _impl_workflow_get_transitions(issue_key=issue_key)  # pragma: no cover


@mcp.tool()
def jira_workflow_transition(
    issue_key: str, transition_id: str, fields: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Transition an issue through workflow.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        transition_id: Transition ID (use get_transitions to find valid IDs)
        fields: Optional fields required by the transition
    """
    return _impl_workflow_transition(  # pragma: no cover
        issue_key=issue_key, transition_id=transition_id, fields=fields
    )


# --- Comment Tools ---


@mcp.tool()
def jira_comment_add(issue_key: str, body: str) -> Dict[str, Any]:
    """Add a comment to an issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        body: Comment text (supports Jira markup)
    """
    return _impl_comment_add(issue_key=issue_key, body=body)  # pragma: no cover


@mcp.tool()
def jira_comment_list(issue_key: str, detail: str | None = None) -> Dict[str, Any]:
    """List all comments on an issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_comment_list(issue_key=issue_key, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_comment_update(issue_key: str, comment_id: str, body: str) -> Dict[str, Any]:
    """Update an existing comment.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        comment_id: Comment ID to update
        body: New comment text
    """
    return _impl_comment_update(  # pragma: no cover
        issue_key=issue_key, comment_id=comment_id, body=body
    )


@mcp.tool()
def jira_comment_delete(issue_key: str, comment_id: str) -> Dict[str, Any]:
    """Delete a comment.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        comment_id: Comment ID to delete
    """
    return _impl_comment_delete(issue_key=issue_key, comment_id=comment_id)  # pragma: no cover


# --- Project Tools ---


@mcp.tool()
def jira_project_list(detail: str | None = None) -> List[Dict[str, Any]]:
    """List all accessible Jira projects.

    Args:
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_project_list(detail=detail)  # pragma: no cover


@mcp.tool()
def jira_project_get(project_key: str, detail: str | None = None) -> Dict[str, Any]:
    """Get project details.

    Args:
        project_key: Project key (e.g., "PROJ")
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_project_get(project_key=project_key, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_project_issue_types(project_key: str) -> List[Dict[str, Any]]:
    """Get available issue types for a project.

    Args:
        project_key: Project key (e.g., "PROJ")
    """
    return _impl_project_issue_types(project_key=project_key)  # pragma: no cover


# --- Board Tools ---


@mcp.tool()
def jira_board_list(project_key: str | None = None) -> Dict[str, Any]:
    """List agile boards, optionally filtered by project.

    Args:
        project_key: Optional project key to filter boards
    """
    return _impl_board_list(project_key=project_key)  # pragma: no cover


@mcp.tool()
def jira_board_get(board_id: str, detail: str | None = None) -> Dict[str, Any]:
    """Get board details.

    Args:
        board_id: Board ID
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_board_get(board_id=board_id, detail=detail)  # pragma: no cover


# --- Sprint Tools ---


@mcp.tool()
def jira_sprint_list(board_id: str, state: str | None = None) -> Dict[str, Any]:
    """List sprints for a board, optionally filtered by state.

    Args:
        board_id: Board ID
        state: Sprint state filter (active, closed, future)
    """
    return _impl_sprint_list(board_id=board_id, state=state)  # pragma: no cover


@mcp.tool()
def jira_sprint_get(sprint_id: str, detail: str | None = None) -> Dict[str, Any]:
    """Get sprint details.

    Args:
        sprint_id: Sprint ID
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_sprint_get(sprint_id=sprint_id, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_sprint_issues(
    sprint_id: str, max_results: int = 50, start_at: int = 0, detail: str | None = None
) -> Dict[str, Any]:
    """Get issues in a sprint.

    Args:
        sprint_id: Sprint ID
        max_results: Maximum results (default: 50)
        start_at: Starting offset for pagination
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_sprint_issues(  # pragma: no cover
        sprint_id=sprint_id, max_results=max_results, start_at=start_at, detail=detail
    )


@mcp.tool()
def jira_sprint_add_issues(sprint_id: str, issue_keys: List[str]) -> Dict[str, Any]:
    """Add issues to a sprint. Moves issues from backlog or another sprint into the specified sprint.

    Args:
        sprint_id: Sprint ID (numeric)
        issue_keys: List of issue keys to add (e.g., ["PROJ-1", "PROJ-2"])
    """
    return _impl_sprint_add_issues(sprint_id=sprint_id, issue_keys=issue_keys)  # pragma: no cover


@mcp.tool()
def jira_sprint_remove_issues(issue_keys: List[str]) -> Dict[str, Any]:
    """Remove issues from their current sprint and move them back to the backlog.

    Args:
        issue_keys: List of issue keys to move to backlog (e.g., ["PROJ-1", "PROJ-2"])
    """
    return _impl_sprint_remove_issues(issue_keys=issue_keys)  # pragma: no cover


# --- User Tools ---


@mcp.tool()
def jira_user_search(query: str, max_results: int = 50, detail: str | None = None) -> List[Dict[str, Any]]:
    """Search for Jira users.

    Args:
        query: Search query (username, email, or display name)
        max_results: Maximum results (default: 50)
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_user_search(query=query, max_results=max_results, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_user_get(username: str, detail: str | None = None) -> Dict[str, Any]:
    """Get user details.

    Args:
        username: Username to look up
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_user_get(username=username, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_user_myself(detail: str | None = None) -> Dict[str, Any]:
    """Get current authenticated user details.

    Args:
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return _impl_user_myself(detail=detail)  # pragma: no cover


# --- Attachment Tools ---


@mcp.tool()
def jira_attachment_add(
    issue_key: str, file_path: str, filename: str | None = None
) -> List[Dict[str, Any]]:
    """Add an attachment to an issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        file_path: Local file path to attach
        filename: Optional custom filename
    """
    return _impl_attachment_add(  # pragma: no cover
        issue_key=issue_key, file_path=file_path, filename=filename
    )


@mcp.tool()
def jira_attachment_get(attachment_id: str) -> Dict[str, Any]:
    """Get attachment metadata.

    Args:
        attachment_id: Attachment ID
    """
    return _impl_attachment_get(attachment_id=attachment_id)  # pragma: no cover


@mcp.tool()
def jira_attachment_delete(attachment_id: str) -> Dict[str, Any]:
    """Delete an attachment.

    Args:
        attachment_id: Attachment ID
    """
    return _impl_attachment_delete(attachment_id=attachment_id)  # pragma: no cover


# --- Priority & Status Tools ---


@mcp.tool()
def jira_priority_list() -> List[Dict[str, Any]]:  # pragma: no cover
    """List all available Jira priorities."""
    return _get_client().list_priorities()  # pragma: no cover


@mcp.tool()
def jira_status_list() -> List[Dict[str, Any]]:  # pragma: no cover
    """List all available Jira statuses."""
    return _get_client().list_statuses()  # pragma: no cover


def main() -> None:
    """Main entry point for the Jira MCP server."""
    try:
        global _client
        config = JiraConfig()  # type: ignore[call-arg]

        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            stream=sys.stderr,
        )

        client = JiraClient(config)
        _client = client

        initialize_issue_tools(config)
        initialize_search_tools(client, config)
        initialize_filter_tools(client, config)
        initialize_workflow_tools(client)
        initialize_comment_tools(client, config)
        initialize_project_tools(client, config)
        initialize_board_tools(client, config)
        initialize_sprint_tools(client, config)
        initialize_user_tools(client, config)
        initialize_attachment_tools(client)

        from importlib.metadata import version as pkg_version

        _version = pkg_version("atlassian-jira-mcp")
        logger.info("Starting Jira MCP Server v%s...", _version)
        logger.info("Jira URL: %s", config.url)
        logger.info("Auth Type: %s", config.auth_type.value if config.auth_type else "auto")
        logger.info("Cache TTL: %ss", config.cache_ttl)
        logger.info("Timeout: %ss", config.timeout)
        logger.info("SSL Verification: %s", "Enabled" if config.verify_ssl else "DISABLED")
        if not config.verify_ssl:
            logger.warning("SSL certificate verification is DISABLED!")
            logger.warning("This should only be used for testing with self-signed certificates.")
        logger.info("Server ready! Use MCP client to interact with Jira.")

        mcp.run()

    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
