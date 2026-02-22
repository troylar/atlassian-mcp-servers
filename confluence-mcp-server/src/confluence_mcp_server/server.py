"""FastMCP 3 server entry point for Confluence MCP Server."""

import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from confluence_mcp_server.client import ConfluenceClient
from confluence_mcp_server.config import ConfluenceConfig

mcp = FastMCP("confluence-mcp-server")

_client: Optional[ConfluenceClient] = None


def _get_client() -> ConfluenceClient:
    if not _client:
        raise RuntimeError("Confluence server not initialized")
    return _client


# --- Health Check ---


@mcp.tool()
def confluence_health_check() -> Dict[str, Any]:  # pragma: no cover
    """Verify connectivity to Confluence instance."""
    return _get_client().health_check()  # pragma: no cover


# --- Page Tools (12 tools) ---


@mcp.tool()
def confluence_page_get(page_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get page details by ID.

    Args:
        page_id: Confluence page ID
    """
    return _get_client().get_page(page_id)  # pragma: no cover


@mcp.tool()
def confluence_page_get_by_title(space_key: str, title: str) -> Dict[str, Any]:  # pragma: no cover
    """Find a page by title within a space.

    Args:
        space_key: Space key (e.g., "DEV")
        title: Page title to search for
    """
    result = _get_client().get_page_by_title(space_key, title)  # pragma: no cover
    if result is None:  # pragma: no cover
        return {"found": False, "message": f"No page titled '{title}' found in space '{space_key}'"}  # pragma: no cover
    return result  # pragma: no cover


@mcp.tool()
def confluence_page_create(
    space_key: str, title: str, body: str, parent_id: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Create a new Confluence page.

    Args:
        space_key: Space key (e.g., "DEV")
        title: Page title
        body: Page content in storage format (XHTML)
        parent_id: Optional parent page ID for nesting
    """
    return _get_client().create_page(space_key, title, body, parent_id=parent_id)  # pragma: no cover


@mcp.tool()
def confluence_page_update(
    page_id: str, title: str, body: str, version: int
) -> Dict[str, Any]:  # pragma: no cover
    """Update an existing Confluence page.

    Args:
        page_id: Page ID to update
        title: New page title
        body: New page content in storage format
        version: Current page version number (for optimistic locking)
    """
    return _get_client().update_page(page_id, title, body, version)  # pragma: no cover


@mcp.tool()
def confluence_page_delete(page_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Delete a Confluence page.

    Args:
        page_id: Page ID to delete
    """
    _get_client().delete_page(page_id)  # pragma: no cover
    return {"success": True, "message": f"Page {page_id} deleted"}  # pragma: no cover


@mcp.tool()
def confluence_page_move(
    page_id: str, target_id: str, position: str = "append"
) -> Dict[str, Any]:  # pragma: no cover
    """Move a page to a new location.

    Args:
        page_id: Page ID to move
        target_id: Target page/space to move to
        position: Position relative to target (append, before, after)
    """
    return _get_client().move_page(page_id, target_id, position)  # pragma: no cover


@mcp.tool()
def confluence_page_copy(
    page_id: str, destination_space: str, title: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Copy a page to another space.

    Args:
        page_id: Page ID to copy
        destination_space: Destination space key
        title: Optional new title for the copy
    """
    return _get_client().copy_page(page_id, destination_space, title)  # pragma: no cover


@mcp.tool()
def confluence_page_children(
    page_id: str, limit: int = 25, start: int = 0
) -> Dict[str, Any]:  # pragma: no cover
    """Get child pages of a page.

    Args:
        page_id: Parent page ID
        limit: Max results (default: 25)
        start: Starting offset
    """
    return _get_client().get_children(page_id, limit, start)  # pragma: no cover


@mcp.tool()
def confluence_page_ancestors(page_id: str) -> List[Dict[str, Any]]:  # pragma: no cover
    """Get ancestor pages (breadcrumb trail).

    Args:
        page_id: Page ID
    """
    return _get_client().get_ancestors(page_id)  # pragma: no cover


@mcp.tool()
def confluence_page_history(page_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get page version history.

    Args:
        page_id: Page ID
    """
    return _get_client().get_history(page_id)  # pragma: no cover


@mcp.tool()
def confluence_page_version(page_id: str, version: int) -> Dict[str, Any]:  # pragma: no cover
    """Get a specific version of a page.

    Args:
        page_id: Page ID
        version: Version number
    """
    return _get_client().get_page_version(page_id, version)  # pragma: no cover


@mcp.tool()
def confluence_page_restore(
    page_id: str, version: int, message: str = ""
) -> Dict[str, Any]:  # pragma: no cover
    """Restore a page to a previous version.

    Args:
        page_id: Page ID
        version: Version number to restore
        message: Optional restore message
    """
    return _get_client().restore_page_version(page_id, version, message)  # pragma: no cover


# --- Search Tools (2 tools) ---


@mcp.tool()
def confluence_search_cql(
    cql: str, limit: int = 25, start: int = 0
) -> Dict[str, Any]:  # pragma: no cover
    """Search Confluence using CQL (Confluence Query Language).

    Args:
        cql: CQL query string
        limit: Max results (default: 25)
        start: Starting offset
    """
    return _get_client().search_cql(cql, limit, start)  # pragma: no cover


@mcp.tool()
def confluence_search(
    query: str,
    space_key: str | None = None,
    content_type: str | None = None,
    limit: int = 25,
    start: int = 0,
) -> Dict[str, Any]:  # pragma: no cover
    """Search Confluence content by text with optional filters.

    Args:
        query: Search text
        space_key: Optional space to search within
        content_type: Optional content type filter (page, blogpost)
        limit: Max results (default: 25)
        start: Starting offset
    """
    return _get_client().search_content(query, space_key, content_type, limit, start)  # pragma: no cover


# --- Space Tools (3 tools) ---


@mcp.tool()
def confluence_space_list(limit: int = 25, start: int = 0) -> Dict[str, Any]:  # pragma: no cover
    """List all accessible Confluence spaces.

    Args:
        limit: Max results (default: 25)
        start: Starting offset
    """
    return _get_client().list_spaces(limit, start)  # pragma: no cover


@mcp.tool()
def confluence_space_get(space_key: str) -> Dict[str, Any]:  # pragma: no cover
    """Get space details.

    Args:
        space_key: Space key (e.g., "DEV")
    """
    return _get_client().get_space(space_key)  # pragma: no cover


@mcp.tool()
def confluence_space_create(
    key: str, name: str, description: str = ""
) -> Dict[str, Any]:  # pragma: no cover
    """Create a new Confluence space.

    Args:
        key: Space key (uppercase, e.g., "DEV")
        name: Space display name
        description: Optional space description
    """
    return _get_client().create_space(key, name, description)  # pragma: no cover


# --- Comment Tools (4 tools) ---


@mcp.tool()
def confluence_comment_add(
    page_id: str, body: str
) -> Dict[str, Any]:  # pragma: no cover
    """Add a comment to a page.

    Args:
        page_id: Page ID
        body: Comment body in storage format
    """
    return _get_client().add_comment(page_id, body)  # pragma: no cover


@mcp.tool()
def confluence_comment_list(
    page_id: str, limit: int = 25, start: int = 0
) -> Dict[str, Any]:  # pragma: no cover
    """List comments on a page.

    Args:
        page_id: Page ID
        limit: Max results
        start: Starting offset
    """
    return _get_client().list_comments(page_id, limit, start)  # pragma: no cover


@mcp.tool()
def confluence_comment_update(
    comment_id: str, body: str, version: int
) -> Dict[str, Any]:  # pragma: no cover
    """Update a comment.

    Args:
        comment_id: Comment ID
        body: New comment body
        version: Current comment version
    """
    return _get_client().update_comment(comment_id, body, version)  # pragma: no cover


@mcp.tool()
def confluence_comment_delete(comment_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Delete a comment.

    Args:
        comment_id: Comment ID
    """
    _get_client().delete_comment(comment_id)  # pragma: no cover
    return {"success": True, "message": f"Comment {comment_id} deleted"}  # pragma: no cover


# --- Attachment Tools (4 tools) ---


@mcp.tool()
def confluence_attachment_add(
    page_id: str, file_path: str, filename: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Add an attachment to a page.

    Args:
        page_id: Page ID
        file_path: Local file path
        filename: Optional custom filename
    """
    return _get_client().add_attachment(page_id, file_path, filename)  # pragma: no cover


@mcp.tool()
def confluence_attachment_list(
    page_id: str, limit: int = 25, start: int = 0
) -> Dict[str, Any]:  # pragma: no cover
    """List attachments on a page.

    Args:
        page_id: Page ID
        limit: Max results
        start: Starting offset
    """
    return _get_client().list_attachments(page_id, limit, start)  # pragma: no cover


@mcp.tool()
def confluence_attachment_get(attachment_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get attachment metadata.

    Args:
        attachment_id: Attachment ID
    """
    return _get_client().get_attachment(attachment_id)  # pragma: no cover


@mcp.tool()
def confluence_attachment_delete(attachment_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Delete an attachment.

    Args:
        attachment_id: Attachment ID
    """
    _get_client().delete_attachment(attachment_id)  # pragma: no cover
    return {"success": True, "message": f"Attachment {attachment_id} deleted"}  # pragma: no cover


# --- Label Tools (3 tools) ---


@mcp.tool()
def confluence_label_add(page_id: str, label: str) -> Dict[str, Any]:  # pragma: no cover
    """Add a label to a page.

    Args:
        page_id: Page ID
        label: Label name
    """
    return _get_client().add_label(page_id, label)  # pragma: no cover


@mcp.tool()
def confluence_label_remove(page_id: str, label: str) -> Dict[str, Any]:  # pragma: no cover
    """Remove a label from a page.

    Args:
        page_id: Page ID
        label: Label name to remove
    """
    _get_client().remove_label(page_id, label)  # pragma: no cover
    return {"success": True, "message": f"Label '{label}' removed from page {page_id}"}  # pragma: no cover


@mcp.tool()
def confluence_label_get(page_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get all labels on a page.

    Args:
        page_id: Page ID
    """
    return _get_client().get_labels(page_id)  # pragma: no cover


# --- Content Conversion (1 tool) ---


@mcp.tool()
def confluence_content_convert(
    value: str, from_repr: str, to_repr: str
) -> Dict[str, Any]:  # pragma: no cover
    """Convert content between representations (storage, editor, view, wiki).

    Args:
        value: Content to convert
        from_repr: Source representation (storage, editor, wiki)
        to_repr: Target representation (storage, editor, view)
    """
    return _get_client().convert_content(value, from_repr, to_repr)  # pragma: no cover


# --- User Tools (2 tools) ---


@mcp.tool()
def confluence_user_get(account_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get user details by account ID.

    Args:
        account_id: Atlassian account ID
    """
    return _get_client().get_user(account_id)  # pragma: no cover


@mcp.tool()
def confluence_user_current() -> Dict[str, Any]:  # pragma: no cover
    """Get current authenticated user details."""
    return _get_client().get_current_user()  # pragma: no cover


# --- Blog Tools (4 tools) ---


@mcp.tool()
def confluence_blog_create(
    space_key: str, title: str, body: str
) -> Dict[str, Any]:  # pragma: no cover
    """Create a blog post.

    Args:
        space_key: Space key
        title: Blog post title
        body: Blog content in storage format
    """
    return _get_client().create_blog(space_key, title, body)  # pragma: no cover


@mcp.tool()
def confluence_blog_list(
    space_key: str, limit: int = 25, start: int = 0
) -> Dict[str, Any]:  # pragma: no cover
    """List blog posts in a space.

    Args:
        space_key: Space key
        limit: Max results
        start: Starting offset
    """
    return _get_client().list_blogs(space_key, limit, start)  # pragma: no cover


@mcp.tool()
def confluence_blog_get(blog_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get blog post details.

    Args:
        blog_id: Blog post ID
    """
    return _get_client().get_blog(blog_id)  # pragma: no cover


@mcp.tool()
def confluence_blog_update(
    blog_id: str, title: str, body: str, version: int
) -> Dict[str, Any]:  # pragma: no cover
    """Update a blog post.

    Args:
        blog_id: Blog post ID
        title: New title
        body: New content in storage format
        version: Current version number
    """
    return _get_client().update_blog(blog_id, title, body, version)  # pragma: no cover


# --- Permission Tools (2 tools) ---


@mcp.tool()
def confluence_permissions_get(page_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get page restrictions/permissions.

    Args:
        page_id: Page ID
    """
    return _get_client().get_page_permissions(page_id)  # pragma: no cover


@mcp.tool()
def confluence_permissions_set(
    page_id: str, restrictions: List[Dict[str, Any]]
) -> Dict[str, Any]:  # pragma: no cover
    """Set page restrictions/permissions.

    Args:
        page_id: Page ID
        restrictions: List of restriction objects
    """
    return _get_client().set_page_permissions(page_id, restrictions)  # pragma: no cover


# --- Macro Tools (1 tool) ---


@mcp.tool()
def confluence_macro_render(
    macro_name: str,
    parameters: Dict[str, str] | None = None,
    body: str | None = None,
    body_type: str = "rich-text-body",
) -> Dict[str, Any]:  # pragma: no cover
    """Render a Confluence macro as storage-format XHTML.

    Returns XHTML that can be embedded in page body content. Works with any
    macro name — built-in (code, toc, panel) or third-party plugins.

    Args:
        macro_name: Macro identifier (e.g., "code", "toc", "panel", "info",
                    "warning", "expand", "note", "excerpt", or any plugin macro)
        parameters: Optional macro parameters as key-value pairs
        body: Optional macro body content
        body_type: Body wrapping — "plain-text-body" for code/noformat (CDATA),
                   "rich-text-body" for panel/expand/info (XHTML). Default: "rich-text-body"

    Examples:
        Table of contents: macro_name="toc"
        Code block: macro_name="code", parameters={"language": "python"},
            body="print('hello')", body_type="plain-text-body"
        Info panel: macro_name="info", parameters={"title": "Note"}, body="<p>Important info</p>"
        Expand section: macro_name="expand", parameters={"title": "Details"}, body="<p>Hidden content</p>"
    """
    return _get_client().render_macro(macro_name, parameters, body, body_type)  # pragma: no cover


def main() -> None:
    """Main entry point for the Confluence MCP server."""
    try:
        global _client
        config = ConfluenceConfig()  # type: ignore[call-arg]
        _client = ConfluenceClient(config)

        print("Starting Confluence MCP Server v1.0.0...")
        print(f"Confluence URL: {config.url}")
        print(f"Auth Type: {config.auth_type.value if config.auth_type else 'auto'}")
        print(f"Timeout: {config.timeout}s")
        print(f"SSL Verification: {'Enabled' if config.verify_ssl else 'DISABLED'}")
        print()
        print("Server ready! Use MCP client to interact with Confluence.")

        mcp.run()

    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
