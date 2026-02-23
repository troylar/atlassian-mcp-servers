"""FastMCP 3 server entry point for Jira MCP Server."""

import sys
from typing import Any, Dict, List

from fastmcp import FastMCP

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.tools.attachment_tools import (
    initialize_attachment_tools,
    jira_attachment_add,
    jira_attachment_delete,
    jira_attachment_get,
)
from jira_mcp_server.tools.board_tools import (
    initialize_board_tools,
    jira_board_get,
    jira_board_list,
)
from jira_mcp_server.tools.comment_tools import (
    initialize_comment_tools,
    jira_comment_add,
    jira_comment_delete,
    jira_comment_list,
    jira_comment_update,
)
from jira_mcp_server.tools.filter_tools import (
    initialize_filter_tools,
    jira_filter_create,
    jira_filter_delete,
    jira_filter_execute,
    jira_filter_get,
    jira_filter_list,
    jira_filter_update,
)
from jira_mcp_server.tools.issue_tools import (
    _get_field_schema,
    initialize_issue_tools,
    jira_issue_create,
    jira_issue_delete,
    jira_issue_get,
    jira_issue_link,
    jira_issue_update,
)
from jira_mcp_server.tools.project_tools import (
    initialize_project_tools,
    jira_project_get,
    jira_project_issue_types,
    jira_project_list,
)
from jira_mcp_server.tools.search_tools import (
    initialize_search_tools,
    jira_search_issues,
    jira_search_jql,
)
from jira_mcp_server.tools.sprint_tools import (
    initialize_sprint_tools,
    jira_sprint_add_issues,
    jira_sprint_get,
    jira_sprint_issues,
    jira_sprint_list,
    jira_sprint_remove_issues,
)
from jira_mcp_server.tools.user_tools import (
    initialize_user_tools,
    jira_user_get,
    jira_user_myself,
    jira_user_search,
)
from jira_mcp_server.tools.workflow_tools import (
    initialize_workflow_tools,
    jira_workflow_get_transitions,
    jira_workflow_transition,
)

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
def jira_issue_create_tool(
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
    return jira_issue_create(  # pragma: no cover
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
def jira_issue_update_tool(
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
    return jira_issue_update(  # pragma: no cover
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
def jira_issue_get_tool(issue_key: str, detail: str | None = None) -> Dict[str, Any]:
    """Retrieve a Jira issue. Returns summary by default; use detail='full' for all fields.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_issue_get(issue_key=issue_key, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_issue_delete_tool(issue_key: str, delete_subtasks: bool = False) -> Dict[str, Any]:
    """Delete a Jira issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        delete_subtasks: Whether to also delete subtasks (default: False)
    """
    return jira_issue_delete(issue_key=issue_key, delete_subtasks=delete_subtasks)  # pragma: no cover


@mcp.tool()
def jira_issue_link_tool(link_type: str, inward_issue: str, outward_issue: str) -> Dict[str, Any]:
    """Link two Jira issues together.

    Args:
        link_type: Link type name (e.g., "Blocks", "Duplicate", "Relates")
        inward_issue: Inward issue key (e.g., "PROJ-123")
        outward_issue: Outward issue key (e.g., "PROJ-456")
    """
    return jira_issue_link(  # pragma: no cover
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
def jira_search_issues_tool(
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
    return jira_search_issues(  # pragma: no cover
        project=project, assignee=assignee, status=status, priority=priority,
        labels=labels, created_after=created_after, created_before=created_before,
        updated_after=updated_after, updated_before=updated_before,
        max_results=max_results, start_at=start_at, detail=detail,
    )


@mcp.tool()
def jira_search_jql_tool(
    jql: str, max_results: int = 50, start_at: int = 0, detail: str | None = None
) -> Dict[str, Any]:
    """Execute a JQL query directly. Supports all JQL operators and ORDER BY.

    Args:
        jql: JQL query string
        max_results: Maximum results (default: 50)
        start_at: Starting offset for pagination
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_search_jql(jql=jql, max_results=max_results, start_at=start_at, detail=detail)  # pragma: no cover


# --- Filter Tools ---


@mcp.tool()
def jira_filter_create_tool(
    name: str, jql: str, description: str | None = None, favourite: bool = False
) -> Dict[str, Any]:
    """Create a new saved filter for reusing complex search queries.

    Args:
        name: Filter name
        jql: JQL query string
        description: Optional filter description
        favourite: Whether to mark as favorite
    """
    return jira_filter_create(name=name, jql=jql, description=description, favourite=favourite)  # pragma: no cover


@mcp.tool()
def jira_filter_list_tool() -> Dict[str, Any]:
    """List all accessible filters."""
    return jira_filter_list()  # pragma: no cover


@mcp.tool()
def jira_filter_get_tool(filter_id: str) -> Dict[str, Any]:
    """Get complete filter details by ID.

    Args:
        filter_id: Filter ID
    """
    return jira_filter_get(filter_id=filter_id)  # pragma: no cover


@mcp.tool()
def jira_filter_execute_tool(
    filter_id: str, max_results: int = 50, start_at: int = 0, detail: str | None = None
) -> Dict[str, Any]:
    """Execute a saved filter and return matching issues.

    Args:
        filter_id: Filter ID
        max_results: Maximum results (default: 50)
        start_at: Starting offset for pagination
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_filter_execute(  # pragma: no cover
        filter_id=filter_id, max_results=max_results, start_at=start_at, detail=detail
    )


@mcp.tool()
def jira_filter_update_tool(
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
    return jira_filter_update(  # pragma: no cover
        filter_id=filter_id, name=name, jql=jql, description=description, favourite=favourite
    )


@mcp.tool()
def jira_filter_delete_tool(filter_id: str) -> Dict[str, Any]:
    """Delete a filter. Only the filter owner can delete it.

    Args:
        filter_id: Filter ID
    """
    return jira_filter_delete(filter_id=filter_id)  # pragma: no cover


# --- Workflow Tools ---


@mcp.tool()
def jira_workflow_get_transitions_tool(issue_key: str) -> Dict[str, Any]:
    """Get available workflow transitions for an issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
    """
    return jira_workflow_get_transitions(issue_key=issue_key)  # pragma: no cover


@mcp.tool()
def jira_workflow_transition_tool(
    issue_key: str, transition_id: str, fields: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Transition an issue through workflow.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        transition_id: Transition ID (use get_transitions to find valid IDs)
        fields: Optional fields required by the transition
    """
    return jira_workflow_transition(  # pragma: no cover
        issue_key=issue_key, transition_id=transition_id, fields=fields
    )


# --- Comment Tools ---


@mcp.tool()
def jira_comment_add_tool(issue_key: str, body: str) -> Dict[str, Any]:
    """Add a comment to an issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        body: Comment text (supports Jira markup)
    """
    return jira_comment_add(issue_key=issue_key, body=body)  # pragma: no cover


@mcp.tool()
def jira_comment_list_tool(issue_key: str, detail: str | None = None) -> Dict[str, Any]:
    """List all comments on an issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_comment_list(issue_key=issue_key, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_comment_update_tool(issue_key: str, comment_id: str, body: str) -> Dict[str, Any]:
    """Update an existing comment.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        comment_id: Comment ID to update
        body: New comment text
    """
    return jira_comment_update(  # pragma: no cover
        issue_key=issue_key, comment_id=comment_id, body=body
    )


@mcp.tool()
def jira_comment_delete_tool(issue_key: str, comment_id: str) -> Dict[str, Any]:
    """Delete a comment.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        comment_id: Comment ID to delete
    """
    return jira_comment_delete(issue_key=issue_key, comment_id=comment_id)  # pragma: no cover


# --- Project Tools ---


@mcp.tool()
def jira_project_list_tool(detail: str | None = None) -> List[Dict[str, Any]]:
    """List all accessible Jira projects.

    Args:
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_project_list(detail=detail)  # pragma: no cover


@mcp.tool()
def jira_project_get_tool(project_key: str, detail: str | None = None) -> Dict[str, Any]:
    """Get project details.

    Args:
        project_key: Project key (e.g., "PROJ")
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_project_get(project_key=project_key, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_project_issue_types_tool(project_key: str) -> List[Dict[str, Any]]:
    """Get available issue types for a project.

    Args:
        project_key: Project key (e.g., "PROJ")
    """
    return jira_project_issue_types(project_key=project_key)  # pragma: no cover


# --- Board Tools ---


@mcp.tool()
def jira_board_list_tool(project_key: str | None = None) -> Dict[str, Any]:
    """List agile boards, optionally filtered by project.

    Args:
        project_key: Optional project key to filter boards
    """
    return jira_board_list(project_key=project_key)  # pragma: no cover


@mcp.tool()
def jira_board_get_tool(board_id: str, detail: str | None = None) -> Dict[str, Any]:
    """Get board details.

    Args:
        board_id: Board ID
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_board_get(board_id=board_id, detail=detail)  # pragma: no cover


# --- Sprint Tools ---


@mcp.tool()
def jira_sprint_list_tool(board_id: str, state: str | None = None) -> Dict[str, Any]:
    """List sprints for a board, optionally filtered by state.

    Args:
        board_id: Board ID
        state: Sprint state filter (active, closed, future)
    """
    return jira_sprint_list(board_id=board_id, state=state)  # pragma: no cover


@mcp.tool()
def jira_sprint_get_tool(sprint_id: str, detail: str | None = None) -> Dict[str, Any]:
    """Get sprint details.

    Args:
        sprint_id: Sprint ID
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_sprint_get(sprint_id=sprint_id, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_sprint_issues_tool(
    sprint_id: str, max_results: int = 50, start_at: int = 0, detail: str | None = None
) -> Dict[str, Any]:
    """Get issues in a sprint.

    Args:
        sprint_id: Sprint ID
        max_results: Maximum results (default: 50)
        start_at: Starting offset for pagination
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_sprint_issues(  # pragma: no cover
        sprint_id=sprint_id, max_results=max_results, start_at=start_at, detail=detail
    )


@mcp.tool()
def jira_sprint_add_issues_tool(sprint_id: str, issue_keys: List[str]) -> Dict[str, Any]:
    """Add issues to a sprint. Moves issues from backlog or another sprint into the specified sprint.

    Args:
        sprint_id: Sprint ID (numeric)
        issue_keys: List of issue keys to add (e.g., ["PROJ-1", "PROJ-2"])
    """
    return jira_sprint_add_issues(sprint_id=sprint_id, issue_keys=issue_keys)  # pragma: no cover


@mcp.tool()
def jira_sprint_remove_issues_tool(issue_keys: List[str]) -> Dict[str, Any]:
    """Remove issues from their current sprint and move them back to the backlog.

    Args:
        issue_keys: List of issue keys to move to backlog (e.g., ["PROJ-1", "PROJ-2"])
    """
    return jira_sprint_remove_issues(issue_keys=issue_keys)  # pragma: no cover


# --- User Tools ---


@mcp.tool()
def jira_user_search_tool(query: str, max_results: int = 50, detail: str | None = None) -> List[Dict[str, Any]]:
    """Search for Jira users.

    Args:
        query: Search query (username, email, or display name)
        max_results: Maximum results (default: 50)
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_user_search(query=query, max_results=max_results, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_user_get_tool(username: str, detail: str | None = None) -> Dict[str, Any]:
    """Get user details.

    Args:
        username: Username to look up
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_user_get(username=username, detail=detail)  # pragma: no cover


@mcp.tool()
def jira_user_myself_tool(detail: str | None = None) -> Dict[str, Any]:
    """Get current authenticated user details.

    Args:
        detail: Response detail level: 'summary' (default) or 'full'
    """
    return jira_user_myself(detail=detail)  # pragma: no cover


# --- Attachment Tools ---


@mcp.tool()
def jira_attachment_add_tool(
    issue_key: str, file_path: str, filename: str | None = None
) -> List[Dict[str, Any]]:
    """Add an attachment to an issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        file_path: Local file path to attach
        filename: Optional custom filename
    """
    return jira_attachment_add(  # pragma: no cover
        issue_key=issue_key, file_path=file_path, filename=filename
    )


@mcp.tool()
def jira_attachment_get_tool(attachment_id: str) -> Dict[str, Any]:
    """Get attachment metadata.

    Args:
        attachment_id: Attachment ID
    """
    return jira_attachment_get(attachment_id=attachment_id)  # pragma: no cover


@mcp.tool()
def jira_attachment_delete_tool(attachment_id: str) -> Dict[str, Any]:
    """Delete an attachment.

    Args:
        attachment_id: Attachment ID
    """
    return jira_attachment_delete(attachment_id=attachment_id)  # pragma: no cover


# --- Priority & Status Tools ---


@mcp.tool()
def jira_priority_list_tool() -> List[Dict[str, Any]]:  # pragma: no cover
    """List all available Jira priorities."""
    return _get_client().list_priorities()  # pragma: no cover


@mcp.tool()
def jira_status_list_tool() -> List[Dict[str, Any]]:  # pragma: no cover
    """List all available Jira statuses."""
    return _get_client().list_statuses()  # pragma: no cover


def main() -> None:
    """Main entry point for the Jira MCP server."""
    try:
        global _client
        config = JiraConfig()  # type: ignore[call-arg]
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
        print(f"Starting Jira MCP Server v{_version}...", file=sys.stderr)
        print(f"Jira URL: {config.url}", file=sys.stderr)
        print(f"Auth Type: {config.auth_type.value if config.auth_type else 'auto'}", file=sys.stderr)
        print(f"Cache TTL: {config.cache_ttl}s", file=sys.stderr)
        print(f"Timeout: {config.timeout}s", file=sys.stderr)
        print(f"SSL Verification: {'Enabled' if config.verify_ssl else 'DISABLED'}", file=sys.stderr)
        if not config.verify_ssl:
            print(file=sys.stderr)
            print("WARNING: SSL certificate verification is DISABLED!", file=sys.stderr)
            print("This should only be used for testing with self-signed certificates.", file=sys.stderr)
        print(file=sys.stderr)
        print("Server ready! Use MCP client to interact with Jira.", file=sys.stderr)

        mcp.run()

    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
