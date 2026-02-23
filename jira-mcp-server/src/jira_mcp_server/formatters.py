"""Response formatters for token-efficient output."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.config import JiraConfig

DEFAULT_SUMMARY_FIELDS = [
    "summary",
    "status",
    "assignee",
    "priority",
    "issuetype",
    "labels",
    "components",
    "resolution",
    "description",
    "created",
    "updated",
    "duedate",
]

SUMMARY_API_FIELDS = ",".join(DEFAULT_SUMMARY_FIELDS)

_DEFAULT_MAX_DESC = 500


def _resolve_detail(detail: Optional[str], config: Optional[JiraConfig]) -> str:
    if detail is not None:
        if detail not in ("summary", "full"):
            raise ValueError(f"Invalid detail level: {detail!r}. Must be 'summary' or 'full'.")
        return detail
    if config is None:
        return "full"
    return config.default_detail


def _get_summary_api_fields(config: Optional[JiraConfig]) -> str:
    if config and config.summary_fields:
        return config.summary_fields
    return SUMMARY_API_FIELDS


def _max_desc(config: Optional[JiraConfig]) -> int:
    return config.max_description_length if config else _DEFAULT_MAX_DESC


def _links(config: Optional[JiraConfig]) -> bool:
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
        return obj.get("displayName") or obj.get("name") or obj.get("value")
    return str(obj)


def _extract_names(items: Any) -> List[str]:
    if not items or not isinstance(items, list):
        return []
    names = [_extract_name(item) for item in items]
    return [n for n in names if n is not None]


def format_issue(raw: Dict[str, Any], config: Optional[JiraConfig]) -> Dict[str, Any]:
    fields = raw.get("fields", {})
    result: Dict[str, Any] = {
        "key": raw.get("key"),
        "summary": fields.get("summary"),
        "description": truncate_text(fields.get("description"), _max_desc(config)),
        "status": _extract_name(fields.get("status")),
        "assignee": _extract_name(fields.get("assignee")),
        "priority": _extract_name(fields.get("priority")),
        "type": _extract_name(fields.get("issuetype")),
        "labels": fields.get("labels", []),
        "components": _extract_names(fields.get("components")),
        "resolution": _extract_name(fields.get("resolution")),
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "duedate": fields.get("duedate"),
    }
    if _links(config):
        result["self"] = raw.get("self")
    return result


def format_issues(raw: Dict[str, Any], config: Optional[JiraConfig]) -> Dict[str, Any]:
    issues = raw.get("issues", [])
    return {
        "total": raw.get("total", 0),
        "startAt": raw.get("startAt", 0),
        "maxResults": raw.get("maxResults", 0),
        "issues": [format_issue(issue, config) for issue in issues],
    }


def format_project(raw: Dict[str, Any], config: Optional[JiraConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "key": raw.get("key"),
        "name": raw.get("name"),
        "description": truncate_text(raw.get("description"), _max_desc(config)),
        "lead": _extract_name(raw.get("lead")),
        "projectTypeKey": raw.get("projectTypeKey"),
    }
    if _links(config):
        result["self"] = raw.get("self")
    return result


def format_projects(
    raw: List[Dict[str, Any]], config: Optional[JiraConfig]
) -> List[Dict[str, Any]]:
    return [format_project(p, config) for p in raw]


def format_comment(raw: Dict[str, Any], config: Optional[JiraConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": raw.get("id"),
        "author": _extract_name(raw.get("author")),
        "body": truncate_text(raw.get("body"), _max_desc(config)),
        "created": raw.get("created"),
        "updated": raw.get("updated"),
    }
    if _links(config):
        result["self"] = raw.get("self")
    return result


def format_comments(raw: Dict[str, Any], config: Optional[JiraConfig]) -> Dict[str, Any]:
    comments = raw.get("comments", [])
    return {
        "total": raw.get("total", len(comments)),
        "comments": [format_comment(c, config) for c in comments],
    }


def format_user(raw: Dict[str, Any], config: Optional[JiraConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "key": raw.get("key"),
        "name": raw.get("name"),
        "displayName": raw.get("displayName"),
        "emailAddress": raw.get("emailAddress"),
        "active": raw.get("active"),
    }
    if _links(config):
        result["self"] = raw.get("self")
    return result


def format_users(
    raw: List[Dict[str, Any]], config: Optional[JiraConfig]
) -> List[Dict[str, Any]]:
    return [format_user(u, config) for u in raw]


def format_sprint(raw: Dict[str, Any], config: Optional[JiraConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "state": raw.get("state"),
        "startDate": raw.get("startDate"),
        "endDate": raw.get("endDate"),
        "completeDate": raw.get("completeDate"),
        "goal": truncate_text(raw.get("goal"), _max_desc(config)),
    }
    if _links(config):
        result["self"] = raw.get("self")
    return result


def format_board(raw: Dict[str, Any], config: Optional[JiraConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "type": raw.get("type"),
    }
    location = raw.get("location")
    if location and isinstance(location, dict):
        result["projectKey"] = location.get("projectKey")
        result["projectName"] = location.get("projectName")
    if _links(config):
        result["self"] = raw.get("self")
    return result
