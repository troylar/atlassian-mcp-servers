"""Response formatters for token-efficient output."""

from typing import Any, Dict, Optional

from bitbucket_mcp_server.config import BitbucketConfig

_DEFAULT_MAX_DESC = 500


def _resolve_detail(detail: Optional[str], config: Optional[BitbucketConfig]) -> str:
    if detail is not None:
        if detail not in ("summary", "full"):
            raise ValueError(f"Invalid detail level: {detail!r}. Must be 'summary' or 'full'.")
        return detail
    if config is None:
        return "full"
    return config.default_detail


def _max_desc(config: Optional[BitbucketConfig]) -> int:
    return config.max_description_length if config else _DEFAULT_MAX_DESC


def _links(config: Optional[BitbucketConfig]) -> bool:
    return config.include_links if config else False


def truncate_text(text: Optional[str], max_length: int) -> Optional[str]:
    if text is None:
        return None
    if max_length == 0:
        return text
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def _extract_name(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("displayName") or obj.get("display_name") or obj.get("name")
    return str(obj)


def format_project(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "key": raw.get("key"),
        "name": raw.get("name"),
        "description": truncate_text(raw.get("description"), _max_desc(config)),
    }
    if _links(config):
        links = raw.get("links", {})
        if isinstance(links, dict):
            self_links = links.get("self", [])
            if isinstance(self_links, list) and self_links:
                result["self"] = self_links[0].get("href")
    return result


def format_projects(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    values = raw.get("values", [])
    return {
        "size": raw.get("size", len(values)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "values": [format_project(p, config) for p in values],
    }


def format_repo(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "slug": raw.get("slug"),
        "name": raw.get("name"),
        "description": truncate_text(raw.get("description"), _max_desc(config)),
    }
    project = raw.get("project")
    if project and isinstance(project, dict):
        result["project"] = project.get("key")
    if _links(config):
        links = raw.get("links", {})
        if isinstance(links, dict):
            clone_links = links.get("clone", [])
            if isinstance(clone_links, list):
                for cl in clone_links:
                    if isinstance(cl, dict) and cl.get("name") == "http":
                        result["cloneUrl"] = cl.get("href")
                        break
    return result


def format_repos(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    values = raw.get("values", [])
    return {
        "size": raw.get("size", len(values)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "values": [format_repo(r, config) for r in values],
    }


def format_branch(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "displayId": raw.get("displayId") or raw.get("name"),
        "latestCommit": raw.get("latestCommit") or raw.get("latestChangeset"),
        "isDefault": raw.get("isDefault", False),
    }
    target = raw.get("target")
    if target and isinstance(target, dict):
        result["latestCommit"] = target.get("hash")
    return result


def format_branches(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    values = raw.get("values", [])
    return {
        "size": raw.get("size", len(values)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "values": [format_branch(v, config) for v in values],
    }


def format_commit(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": raw.get("id") or raw.get("hash"),
        "displayId": raw.get("displayId"),
        "message": truncate_text(raw.get("message"), _max_desc(config)),
        "author": _extract_name(raw.get("author")),
        "authorTimestamp": raw.get("authorTimestamp") or raw.get("date"),
    }
    if _links(config):
        links = raw.get("links", {})
        if isinstance(links, dict):
            self_links = links.get("self", [])
            if isinstance(self_links, list) and self_links:
                result["self"] = self_links[0].get("href")
    return result


def format_commits(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    values = raw.get("values", [])
    return {
        "size": raw.get("size", len(values)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "values": [format_commit(c, config) for c in values],
    }


def format_pr(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "description": truncate_text(raw.get("description"), _max_desc(config)),
        "state": raw.get("state"),
        "author": _extract_name(raw.get("author", {}).get("user") if isinstance(raw.get("author"), dict) else None),
    }
    from_ref = raw.get("fromRef") or raw.get("source")
    to_ref = raw.get("toRef") or raw.get("destination")
    if from_ref and isinstance(from_ref, dict):
        branch = from_ref.get("displayId") or from_ref.get("branch", {}).get("name")
        result["sourceBranch"] = branch
    if to_ref and isinstance(to_ref, dict):
        branch = to_ref.get("displayId") or to_ref.get("branch", {}).get("name")
        result["targetBranch"] = branch
    reviewers = raw.get("reviewers", [])
    if isinstance(reviewers, list):
        result["reviewers"] = [_extract_name(r.get("user") if isinstance(r, dict) else r) for r in reviewers]
    if _links(config):
        links = raw.get("links", {})
        if isinstance(links, dict):
            self_links = links.get("self", [])
            if isinstance(self_links, list) and self_links:
                result["self"] = self_links[0].get("href")
    return result


def format_prs(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    values = raw.get("values", [])
    return {
        "size": raw.get("size", len(values)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "values": [format_pr(p, config) for p in values],
    }


def format_pr_comment(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": raw.get("id"),
        "text": truncate_text(raw.get("text") or raw.get("content", {}).get("raw"), _max_desc(config)),
        "author": _extract_name(raw.get("author")),
        "createdDate": raw.get("createdDate") or raw.get("created_on"),
    }
    return result


def format_pr_comments(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    values = raw.get("values", [])
    return {
        "size": raw.get("size", len(values)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "values": [format_pr_comment(c, config) for c in values],
    }


def format_tag(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    return {
        "displayId": raw.get("displayId") or raw.get("name"),
        "hash": raw.get("hash") or raw.get("latestCommit"),
        "message": truncate_text(raw.get("message"), _max_desc(config)),
    }


def format_tags(raw: Dict[str, Any], config: Optional[BitbucketConfig]) -> Dict[str, Any]:
    values = raw.get("values", [])
    return {
        "size": raw.get("size", len(values)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "values": [format_tag(t, config) for t in values],
    }
