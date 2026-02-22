"""MCP tools for issue management."""

from typing import Any, Dict, List, Optional

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.models import FieldSchema, FieldType, FieldValidationError
from jira_mcp_server.schema_cache import SchemaCache
from jira_mcp_server.utils.text import sanitize_long_text, sanitize_text, sanitize_value
from jira_mcp_server.validators import FieldValidator

_client: Optional[JiraClient] = None
_cache: Optional[SchemaCache] = None
_validator: Optional[FieldValidator] = None


def initialize_issue_tools(config: JiraConfig) -> None:
    global _client, _cache, _validator
    _client = JiraClient(config)
    _cache = SchemaCache(ttl_seconds=config.cache_ttl)
    _validator = FieldValidator()


def _get_field_schema(project: str, issue_type: str) -> List[FieldSchema]:
    if not _cache or not _client:
        raise RuntimeError("Issue tools not initialized")

    cached_schema = _cache.get(project, issue_type)
    if cached_schema is not None:
        return cached_schema

    raw_schema = _client.get_project_schema(project, issue_type)

    field_schemas: List[FieldSchema] = []
    for field_data in raw_schema:
        field_key = field_data.get("key", "")
        field_name = field_data.get("name", field_key)
        field_required = field_data.get("required", False)

        schema_info = field_data.get("schema", {})
        schema_type = schema_info.get("type", "string")
        is_custom = field_data.get("custom", field_key.startswith("customfield_"))

        if schema_type == "number":
            field_type = FieldType.NUMBER
        elif schema_type == "date":
            field_type = FieldType.DATE
        elif schema_type == "datetime":
            field_type = FieldType.DATETIME
        elif schema_type == "user":
            field_type = FieldType.USER
        elif schema_type == "option":
            field_type = FieldType.OPTION
        elif schema_type == "array":
            field_type = FieldType.ARRAY
        else:
            field_type = FieldType.STRING

        allowed_values = None
        if "allowedValues" in field_data:
            allowed_values = [v.get("value") or v.get("name") for v in field_data["allowedValues"]]

        field_schema = FieldSchema(
            key=field_key,
            name=field_name,
            type=field_type,
            required=field_required,
            allowed_values=allowed_values,
            custom=is_custom,
            schema_type=str(schema_info),
        )
        field_schemas.append(field_schema)

    _cache.set(project, issue_type, field_schemas)
    return field_schemas


def jira_issue_create(
    project: str,
    summary: str,
    issue_type: str = "Task",
    description: str = "",
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    labels: Optional[List[str]] = None,
    due_date: Optional[str] = None,
    **custom_fields: Any,
) -> Dict[str, Any]:
    if not _client or not _validator:
        raise RuntimeError("Issue tools not initialized")

    try:
        schema = _get_field_schema(project, issue_type)
    except Exception as e:
        raise ValueError(f"Failed to get project schema: {str(e)}")

    fields: Dict[str, Any] = {
        "project": {"key": project},
        "summary": sanitize_text(summary),
        "issuetype": {"name": issue_type},
    }

    if description:
        fields["description"] = sanitize_long_text(description)
    if priority:
        fields["priority"] = {"name": sanitize_text(priority)}
    if assignee:
        fields["assignee"] = {"name": sanitize_text(assignee)}
    if labels:
        fields["labels"] = [sanitize_text(label) for label in labels]
    if due_date:
        fields["duedate"] = sanitize_text(due_date)

    for key, value in custom_fields.items():
        fields[key] = sanitize_value(value)

    try:
        _validator.validate_fields(fields, schema)
    except FieldValidationError as e:
        raise ValueError(f"Validation failed: {str(e)}")

    issue_data = {"fields": fields}
    try:
        return _client.create_issue(issue_data)
    except Exception as e:
        raise ValueError(f"Failed to create issue: {str(e)}")


def jira_issue_update(
    issue_key: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    labels: Optional[List[str]] = None,
    due_date: Optional[str] = None,
    **custom_fields: Any,
) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Issue tools not initialized")

    fields: Dict[str, Any] = {}
    if summary is not None:
        fields["summary"] = sanitize_text(summary)
    if description is not None:
        fields["description"] = sanitize_long_text(description)
    if priority is not None:
        fields["priority"] = {"name": sanitize_text(priority)}
    if assignee is not None:
        fields["assignee"] = {"name": sanitize_text(assignee)}
    if labels is not None:
        fields["labels"] = [sanitize_text(label) for label in labels]
    if due_date is not None:
        fields["duedate"] = sanitize_text(due_date)

    for key, value in custom_fields.items():
        fields[key] = sanitize_value(value)

    if not fields:
        raise ValueError("No fields provided to update")

    update_data = {"fields": fields}
    try:
        _client.update_issue(issue_key, update_data)
        return _client.get_issue(issue_key)
    except Exception as e:
        raise ValueError(f"Failed to update issue: {str(e)}")


def jira_issue_get(issue_key: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Issue tools not initialized")
    try:
        return _client.get_issue(issue_key)
    except Exception as e:
        raise ValueError(f"Failed to get issue: {str(e)}")


def jira_issue_delete(issue_key: str, delete_subtasks: bool = False) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Issue tools not initialized")
    if not issue_key or not issue_key.strip():
        raise ValueError("Issue key cannot be empty")
    try:
        _client.delete_issue(issue_key, delete_subtasks=delete_subtasks)
        return {"success": True, "message": f"Issue {issue_key} deleted successfully"}
    except Exception as e:
        raise ValueError(f"Failed to delete issue: {str(e)}")


def jira_issue_link(link_type: str, inward_issue: str, outward_issue: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError("Issue tools not initialized")
    if not link_type or not link_type.strip():
        raise ValueError("Link type cannot be empty")
    if not inward_issue or not inward_issue.strip():
        raise ValueError("Inward issue key cannot be empty")
    if not outward_issue or not outward_issue.strip():
        raise ValueError("Outward issue key cannot be empty")
    try:
        _client.link_issues(link_type=sanitize_text(link_type), inward_issue=inward_issue, outward_issue=outward_issue)
        return {
            "success": True,
            "message": f"Linked {inward_issue} -> {outward_issue} ({link_type})",
        }
    except Exception as e:
        raise ValueError(f"Failed to link issues: {str(e)}")
