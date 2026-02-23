"""FastMCP 3 server entry point for Bitbucket MCP Server."""

import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from bitbucket_mcp_server.client import BitbucketClient
from bitbucket_mcp_server.config import BitbucketConfig
from bitbucket_mcp_server.formatters import (
    _resolve_detail,
    format_branch,
    format_branches,
    format_commit,
    format_commits,
    format_pr,
    format_pr_comments,
    format_project,
    format_projects,
    format_prs,
    format_repo,
    format_repos,
    format_tags,
)

mcp = FastMCP("bitbucket-mcp-server")

_client: Optional[BitbucketClient] = None
_config: Optional[BitbucketConfig] = None


def _get_client() -> BitbucketClient:
    if not _client:
        raise RuntimeError("Bitbucket server not initialized")
    return _client


# --- Health Check ---


@mcp.tool()
def bitbucket_health_check() -> Dict[str, Any]:  # pragma: no cover
    """Verify connectivity to Bitbucket instance."""
    return _get_client().health_check()  # pragma: no cover


# --- Project Tools (3 tools) ---


@mcp.tool()
def bitbucket_project_list(
    limit: int = 25, start: int = 0, detail: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """List Bitbucket projects.

    Args:
        limit: Max results (default: 25)
        start: Starting offset
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().list_projects(limit, start)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_projects(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_project_get(project_key: str, detail: str | None = None) -> Dict[str, Any]:  # pragma: no cover
    """Get project details.

    Args:
        project_key: Project key
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().get_project(project_key)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_project(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_project_create(key: str, name: str, description: str = "") -> Dict[str, Any]:  # pragma: no cover
    """Create a new project.

    Args:
        key: Project key
        name: Project name
        description: Optional description
    """
    return _get_client().create_project(key, name, description)  # pragma: no cover


# --- Repository Tools (5 tools) ---


@mcp.tool()
def bitbucket_repo_list(
    project: str, limit: int = 25, start: int = 0, detail: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """List repositories in a project.

    Args:
        project: Project key
        limit: Max results
        start: Starting offset
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().list_repos(project, limit, start)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_repos(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_repo_get(project: str, repo: str, detail: str | None = None) -> Dict[str, Any]:  # pragma: no cover
    """Get repository details.

    Args:
        project: Project key
        repo: Repository slug
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().get_repo(project, repo)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_repo(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_repo_create(project: str, name: str, description: str = "") -> Dict[str, Any]:  # pragma: no cover
    """Create a new repository.

    Args:
        project: Project key
        name: Repository name
        description: Optional description
    """
    return _get_client().create_repo(project, name, description)  # pragma: no cover


@mcp.tool()
def bitbucket_repo_delete(project: str, repo: str) -> Dict[str, Any]:  # pragma: no cover
    """Delete a repository.

    Args:
        project: Project key
        repo: Repository slug
    """
    _get_client().delete_repo(project, repo)  # pragma: no cover
    return {"success": True, "message": f"Repository {repo} deleted"}  # pragma: no cover


@mcp.tool()
def bitbucket_repo_fork(project: str, repo: str, name: str | None = None) -> Dict[str, Any]:  # pragma: no cover
    """Fork a repository.

    Args:
        project: Project key
        repo: Repository slug
        name: Optional fork name
    """
    return _get_client().fork_repo(project, repo, name)  # pragma: no cover


# --- Branch Tools (4 tools) ---


@mcp.tool()
def bitbucket_branch_list(  # pragma: no cover
    project: str, repo: str, limit: int = 25, start: int = 0, detail: str | None = None
) -> Dict[str, Any]:
    """List branches in a repository.

    Args:
        project: Project key
        repo: Repository slug
        limit: Max results
        start: Starting offset
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().list_branches(project, repo, limit, start)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_branches(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_branch_create(project: str, repo: str, name: str, start_point: str) -> Dict[str, Any]:  # pragma: no cover
    """Create a new branch.

    Args:
        project: Project key
        repo: Repository slug
        name: Branch name
        start_point: Starting commit hash or branch name
    """
    return _get_client().create_branch(project, repo, name, start_point)  # pragma: no cover


@mcp.tool()
def bitbucket_branch_delete(project: str, repo: str, name: str) -> Dict[str, Any]:  # pragma: no cover
    """Delete a branch.

    Args:
        project: Project key
        repo: Repository slug
        name: Branch name
    """
    _get_client().delete_branch(project, repo, name)  # pragma: no cover
    return {"success": True, "message": f"Branch {name} deleted"}  # pragma: no cover


@mcp.tool()
def bitbucket_branch_default(
    project: str, repo: str, detail: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Get the default branch of a repository.

    Args:
        project: Project key
        repo: Repository slug
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().get_default_branch(project, repo)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_branch(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


# --- Commit Tools (3 tools) ---


@mcp.tool()
def bitbucket_commit_list(
    project: str, repo: str, branch: str | None = None, limit: int = 25, start: int = 0,
    detail: str | None = None,
) -> Dict[str, Any]:  # pragma: no cover
    """List commits in a repository.

    Args:
        project: Project key
        repo: Repository slug
        branch: Optional branch to list commits from
        limit: Max results
        start: Starting offset
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().list_commits(project, repo, branch, limit, start)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_commits(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_commit_get(
    project: str, repo: str, commit_id: str, detail: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Get commit details.

    Args:
        project: Project key
        repo: Repository slug
        commit_id: Commit hash
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().get_commit(project, repo, commit_id)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_commit(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_commit_diff(project: str, repo: str, commit_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get diff for a commit.

    Args:
        project: Project key
        repo: Repository slug
        commit_id: Commit hash
    """
    return _get_client().get_commit_diff(project, repo, commit_id)  # pragma: no cover


# --- PR Tools (10 tools) ---


@mcp.tool()
def bitbucket_pr_list(
    project: str, repo: str, state: str = "OPEN", limit: int = 25, start: int = 0,
    detail: str | None = None,
) -> Dict[str, Any]:  # pragma: no cover
    """List pull requests.

    Args:
        project: Project key
        repo: Repository slug
        state: PR state filter (OPEN, MERGED, DECLINED, ALL)
        limit: Max results
        start: Starting offset
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().list_prs(project, repo, state, limit, start)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_prs(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_pr_get(
    project: str, repo: str, pr_id: int, detail: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Get pull request details.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: Pull request ID
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().get_pr(project, repo, pr_id)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_pr(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_pr_create(
    project: str,
    repo: str,
    title: str,
    source_branch: str,
    target_branch: str,
    description: str = "",
    reviewers: List[str] | None = None,
) -> Dict[str, Any]:  # pragma: no cover
    """Create a pull request.

    Args:
        project: Project key
        repo: Repository slug
        title: PR title
        source_branch: Source branch name
        target_branch: Target branch name
        description: Optional PR description
        reviewers: Optional list of reviewer usernames (UUIDs for Cloud, usernames for DC)
    """
    return _get_client().create_pr(  # pragma: no cover
        project, repo, title, source_branch, target_branch, description, reviewers
    )


@mcp.tool()
def bitbucket_pr_update(
    project: str, repo: str, pr_id: int, title: str | None = None, description: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Update a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        title: New title
        description: New description
    """
    return _get_client().update_pr(project, repo, pr_id, title, description)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_merge(project: str, repo: str, pr_id: int, message: str = "") -> Dict[str, Any]:  # pragma: no cover
    """Merge a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        message: Optional merge commit message
    """
    return _get_client().merge_pr(project, repo, pr_id, message)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_decline(project: str, repo: str, pr_id: int) -> Dict[str, Any]:  # pragma: no cover
    """Decline a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
    """
    return _get_client().decline_pr(project, repo, pr_id)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_reopen(project: str, repo: str, pr_id: int) -> Dict[str, Any]:  # pragma: no cover
    """Reopen a declined pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
    """
    return _get_client().reopen_pr(project, repo, pr_id)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_diff(project: str, repo: str, pr_id: int) -> Dict[str, Any]:  # pragma: no cover
    """Get pull request diff.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
    """
    return _get_client().get_pr_diff(project, repo, pr_id)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_commits(
    project: str, repo: str, pr_id: int, detail: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Get commits in a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().get_pr_commits(project, repo, pr_id)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_commits(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_pr_activities(project: str, repo: str, pr_id: int) -> Dict[str, Any]:  # pragma: no cover
    """Get pull request activity log.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
    """
    return _get_client().get_pr_activities(project, repo, pr_id)  # pragma: no cover


# --- PR Comment Tools (4 tools) ---


@mcp.tool()
def bitbucket_pr_comment_add(
    project: str, repo: str, pr_id: int, text: str,
    file_path: str | None = None, line: int | None = None,
) -> Dict[str, Any]:  # pragma: no cover
    """Add a comment to a pull request. Supports inline comments.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        text: Comment text
        file_path: Optional file path for inline comment
        line: Optional line number for inline comment
    """
    return _get_client().add_pr_comment(project, repo, pr_id, text, file_path, line)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_comment_list(
    project: str, repo: str, pr_id: int, detail: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """List comments on a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().list_pr_comments(project, repo, pr_id)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_pr_comments(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_pr_comment_update(
    project: str, repo: str, pr_id: int, comment_id: int, text: str
) -> Dict[str, Any]:  # pragma: no cover
    """Update a PR comment.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        comment_id: Comment ID
        text: New comment text
    """
    return _get_client().update_pr_comment(project, repo, pr_id, comment_id, text)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_comment_delete(
    project: str, repo: str, pr_id: int, comment_id: int
) -> Dict[str, Any]:  # pragma: no cover
    """Delete a PR comment.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        comment_id: Comment ID
    """
    _get_client().delete_pr_comment(project, repo, pr_id, comment_id)  # pragma: no cover
    return {"success": True, "message": f"Comment {comment_id} deleted"}  # pragma: no cover


# --- PR Review Tools (3 tools) ---


@mcp.tool()
def bitbucket_pr_approve(project: str, repo: str, pr_id: int) -> Dict[str, Any]:  # pragma: no cover
    """Approve a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
    """
    return _get_client().approve_pr(project, repo, pr_id)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_unapprove(project: str, repo: str, pr_id: int) -> Dict[str, Any]:  # pragma: no cover
    """Remove approval from a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
    """
    _get_client().unapprove_pr(project, repo, pr_id)  # pragma: no cover
    return {"success": True, "message": f"PR {pr_id} approval removed"}  # pragma: no cover


@mcp.tool()
def bitbucket_pr_needs_work(project: str, repo: str, pr_id: int) -> Dict[str, Any]:  # pragma: no cover
    """Mark a pull request as needs work (Data Center only).

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
    """
    return _get_client().needs_work_pr(project, repo, pr_id)  # pragma: no cover


# --- PR Reviewer Tools (3 tools) ---


@mcp.tool()
def bitbucket_pr_reviewer_list(project: str, repo: str, pr_id: int) -> Dict[str, Any]:  # pragma: no cover
    """List reviewers on a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
    """
    return _get_client().get_pr_reviewers(project, repo, pr_id)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_reviewer_add(project: str, repo: str, pr_id: int, username: str) -> Dict[str, Any]:  # pragma: no cover
    """Add a reviewer to a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        username: Reviewer username (UUID for Cloud, username for Data Center)
    """
    return _get_client().add_pr_reviewer(project, repo, pr_id, username)  # pragma: no cover


@mcp.tool()
def bitbucket_pr_reviewer_remove(  # pragma: no cover
    project: str, repo: str, pr_id: int, username: str
) -> Dict[str, Any]:  # pragma: no cover
    """Remove a reviewer from a pull request.

    Args:
        project: Project key
        repo: Repository slug
        pr_id: PR ID
        username: Reviewer username to remove
    """
    return _get_client().remove_pr_reviewer(project, repo, pr_id, username)  # pragma: no cover


# --- File Tools (2 tools) ---


@mcp.tool()
def bitbucket_file_browse(
    project: str, repo: str, path: str = "", at: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Browse files in a repository.

    Args:
        project: Project key
        repo: Repository slug
        path: File/directory path (empty for root)
        at: Optional branch/tag/commit to browse at
    """
    return _get_client().browse_files(project, repo, path, at)  # pragma: no cover


@mcp.tool()
def bitbucket_file_content(
    project: str, repo: str, path: str, at: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """Get file content.

    Args:
        project: Project key
        repo: Repository slug
        path: File path
        at: Optional branch/tag/commit
    """
    return _get_client().get_file_content(project, repo, path, at)  # pragma: no cover


# --- Tag Tools (3 tools) ---


@mcp.tool()
def bitbucket_tag_list(
    project: str, repo: str, limit: int = 25, start: int = 0, detail: str | None = None
) -> Dict[str, Any]:  # pragma: no cover
    """List tags in a repository.

    Args:
        project: Project key
        repo: Repository slug
        limit: Max results
        start: Starting offset
        detail: Response detail level ('summary' or 'full'). Default from config.
    """
    resolved = _resolve_detail(detail, _config)  # pragma: no cover
    raw = _get_client().list_tags(project, repo, limit, start)  # pragma: no cover
    if resolved == "summary":  # pragma: no cover
        return format_tags(raw, _config)  # pragma: no cover
    return raw  # pragma: no cover


@mcp.tool()
def bitbucket_tag_create(
    project: str, repo: str, name: str, target: str, message: str = ""
) -> Dict[str, Any]:  # pragma: no cover
    """Create a tag.

    Args:
        project: Project key
        repo: Repository slug
        name: Tag name
        target: Commit hash to tag
        message: Optional tag message
    """
    return _get_client().create_tag(project, repo, name, target, message)  # pragma: no cover


@mcp.tool()
def bitbucket_tag_delete(project: str, repo: str, name: str) -> Dict[str, Any]:  # pragma: no cover
    """Delete a tag.

    Args:
        project: Project key
        repo: Repository slug
        name: Tag name
    """
    _get_client().delete_tag(project, repo, name)  # pragma: no cover
    return {"success": True, "message": f"Tag {name} deleted"}  # pragma: no cover


# --- Webhook Tools (3 tools) ---


@mcp.tool()
def bitbucket_webhook_list(project: str, repo: str) -> Dict[str, Any]:  # pragma: no cover
    """List webhooks on a repository.

    Args:
        project: Project key
        repo: Repository slug
    """
    return _get_client().list_webhooks(project, repo)  # pragma: no cover


@mcp.tool()
def bitbucket_webhook_create(
    project: str, repo: str, name: str, url: str, events: List[str]
) -> Dict[str, Any]:  # pragma: no cover
    """Create a webhook.

    Args:
        project: Project key
        repo: Repository slug
        name: Webhook name
        url: Webhook URL
        events: List of event types to trigger on
    """
    return _get_client().create_webhook(project, repo, name, url, events)  # pragma: no cover


@mcp.tool()
def bitbucket_webhook_delete(project: str, repo: str, webhook_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Delete a webhook.

    Args:
        project: Project key
        repo: Repository slug
        webhook_id: Webhook ID
    """
    _get_client().delete_webhook(project, repo, webhook_id)  # pragma: no cover
    return {"success": True, "message": f"Webhook {webhook_id} deleted"}  # pragma: no cover


# --- Build Status Tools (2 tools) ---


@mcp.tool()
def bitbucket_build_status_get(commit_id: str) -> Dict[str, Any]:  # pragma: no cover
    """Get build status for a commit.

    Args:
        commit_id: Commit hash
    """
    return _get_client().get_build_status(commit_id)  # pragma: no cover


@mcp.tool()
def bitbucket_build_status_set(
    commit_id: str, state: str, key: str, url: str, description: str = ""
) -> Dict[str, Any]:  # pragma: no cover
    """Set build status for a commit.

    Args:
        commit_id: Commit hash
        state: Build state (SUCCESSFUL, FAILED, INPROGRESS)
        key: Build key identifier
        url: Build URL
        description: Optional build description
    """
    return _get_client().set_build_status(commit_id, state, key, url, description)  # pragma: no cover


# --- Diff Tool (1 tool) ---


@mcp.tool()
def bitbucket_diff(project: str, repo: str, from_ref: str, to_ref: str) -> Dict[str, Any]:  # pragma: no cover
    """Get diff between two refs (branches, commits, tags).

    Args:
        project: Project key
        repo: Repository slug
        from_ref: Source ref
        to_ref: Target ref
    """
    return _get_client().get_diff(project, repo, from_ref, to_ref)  # pragma: no cover


def main() -> None:
    """Main entry point for the Bitbucket MCP server."""
    try:
        global _client, _config
        config = BitbucketConfig()  # type: ignore[call-arg]
        _config = config
        _client = BitbucketClient(config)

        from importlib.metadata import version as pkg_version

        _version = pkg_version("atlassian-bitbucket-mcp")
        print(f"Starting Bitbucket MCP Server v{_version}...", file=sys.stderr)
        print(f"Bitbucket URL: {config.url}", file=sys.stderr)
        print(f"Auth Type: {config.auth_type.value if config.auth_type else 'auto'}", file=sys.stderr)
        print(f"Timeout: {config.timeout}s", file=sys.stderr)
        print(f"SSL Verification: {'Enabled' if config.verify_ssl else 'DISABLED'}", file=sys.stderr)
        if config.workspace:
            print(f"Workspace: {config.workspace}", file=sys.stderr)
        print(file=sys.stderr)
        print("Server ready! Use MCP client to interact with Bitbucket.", file=sys.stderr)

        mcp.run()

    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
