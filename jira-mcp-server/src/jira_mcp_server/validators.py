"""Field validation logic and input security helpers (OWASP ASVS V5)."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jira_mcp_server.models import FieldSchema, FieldType, FieldValidationError

# --- Security validators (OWASP ASVS V5) ---

# Jira issue keys: PROJECT-123
_ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")

# Generic numeric IDs (filter IDs, attachment IDs, etc.)
_NUMERIC_ID_RE = re.compile(r"^\d+$")

# Project keys: uppercase letters, digits, underscore
_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

MAX_ID_LENGTH = 255


def validate_issue_key(value: str, name: str = "issue_key") -> str:
    """Validate a Jira issue key (e.g., PROJ-123)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if len(value) > MAX_ID_LENGTH:
        raise ValueError(f"{name} exceeds maximum length of {MAX_ID_LENGTH}")
    if not _ISSUE_KEY_RE.match(value):
        raise ValueError(f"{name} must match format PROJECT-123 (uppercase project key, dash, number)")
    return value


def validate_project_key(value: str, name: str = "project_key") -> str:
    """Validate a Jira project key (e.g., PROJ)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if len(value) > MAX_ID_LENGTH:
        raise ValueError(f"{name} exceeds maximum length of {MAX_ID_LENGTH}")
    if not _PROJECT_KEY_RE.match(value):
        raise ValueError(f"{name} must be uppercase letters/digits/underscores starting with a letter")
    return value


def validate_numeric_id(value: str, name: str = "id") -> str:
    """Validate a numeric ID string (filter, board, sprint, attachment, comment)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if not _NUMERIC_ID_RE.match(value):
        raise ValueError(f"{name} must be a numeric string")
    return value


def validate_max_results(value: int, ceiling: int = 100) -> int:
    """Cap max_results to a safe ceiling."""
    if value < 0:
        raise ValueError("max_results must not be negative")
    return min(value, ceiling)


def validate_file_path(file_path: str) -> str:
    """Validate a file path for attachment upload.

    Rejects path traversal, symlinks to outside dirs, and non-files.
    """
    if not file_path or not file_path.strip():
        raise ValueError("file_path must not be empty")

    resolved = Path(file_path).resolve()

    if ".." in Path(file_path).parts:
        raise ValueError("file_path must not contain '..' path traversal")

    if not resolved.exists():
        raise ValueError(f"File not found: {file_path}")

    if not resolved.is_file():
        raise ValueError(f"Path is not a regular file: {file_path}")

    if resolved.is_symlink():  # pragma: no cover – resolve() follows symlinks
        raise ValueError(f"Symlinks are not allowed: {file_path}")

    return str(resolved)


def validate_enum(value: str, name: str, allowed: frozenset[str]) -> str:
    """Validate that a value is in an allowed set (case-insensitive)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    normalized = value.strip().lower()
    allowed_lower = {v.lower() for v in allowed}
    if normalized not in allowed_lower:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}")
    for v in allowed:
        if v.lower() == normalized:
            return v
    return value  # pragma: no cover


SPRINT_STATES = frozenset({"active", "closed", "future"})


def _safe_error_text(response_text: str, max_len: int = 200) -> str:
    """Truncate response text for error messages, stripping potential secrets."""
    text = response_text[:max_len]
    text = re.sub(r"(Bearer|Basic)\s+[A-Za-z0-9+/=_-]+", "[REDACTED]", text)
    return text


# --- Field schema validators (existing) ---


class FieldValidator:
    """Validates Jira field values against field schemas."""

    def validate_required_fields(self, fields: Dict[str, Any], schema: List[FieldSchema]) -> List[str]:
        errors: List[str] = []
        required_keys = {f.key for f in schema if f.required}
        provided_keys = set(fields.keys())
        missing = required_keys - provided_keys
        if missing:
            missing_names = [f.name for f in schema if f.key in missing]
            errors.append(f"Missing required fields: {', '.join(missing_names)}")
        return errors

    def validate_custom_field_values(self, fields: Dict[str, Any], schema: List[FieldSchema]) -> List[str]:
        errors: List[str] = []
        schema_map = {f.key: f for f in schema}
        for field_key, value in fields.items():
            if field_key not in schema_map:
                continue
            field_schema = schema_map[field_key]
            is_valid, error_msg = self._validate_field_value(value, field_schema)
            if not is_valid and error_msg:
                errors.append(error_msg)
        return errors

    def _validate_field_value(self, value: Any, schema: FieldSchema) -> Tuple[bool, Optional[str]]:
        if schema.required and value is None:
            return False, f"Field '{schema.name}' is required"
        if value is None:
            return True, None

        if schema.type == FieldType.NUMBER:
            if not isinstance(value, (int, float)):
                return False, f"Field '{schema.name}' must be a number, got {type(value).__name__}"
        elif schema.type == FieldType.STRING:
            if not isinstance(value, str):
                return False, f"Field '{schema.name}' must be a string, got {type(value).__name__}"
        elif schema.type == FieldType.OPTION:
            if schema.allowed_values:
                if value not in schema.allowed_values:
                    allowed_str = ", ".join(schema.allowed_values)
                    return (
                        False,
                        f"Invalid value '{value}' for field '{schema.name}'. Allowed values: {allowed_str}",
                    )
        elif schema.type == FieldType.MULTI_SELECT:
            if not isinstance(value, list):
                return False, f"Field '{schema.name}' must be a list"
            if schema.allowed_values:
                for item in value:
                    if item not in schema.allowed_values:
                        allowed_str = ", ".join(schema.allowed_values)
                        return (
                            False,
                            f"Invalid value '{item}' in field '{schema.name}'. Allowed values: {allowed_str}",
                        )
        elif schema.type == FieldType.ARRAY:
            if not isinstance(value, list):
                return False, f"Field '{schema.name}' must be an array"
        elif schema.type == FieldType.DATE:
            if not isinstance(value, str):
                return False, f"Field '{schema.name}' must be a date string (ISO format)"
        elif schema.type == FieldType.DATETIME:
            if not isinstance(value, str):
                return False, f"Field '{schema.name}' must be a datetime string (ISO format)"

        return True, None

    def validate_fields(self, fields: Dict[str, Any], schema: List[FieldSchema]) -> None:
        errors: List[str] = []
        errors.extend(self.validate_required_fields(fields, schema))
        errors.extend(self.validate_custom_field_values(fields, schema))
        if errors:
            raise FieldValidationError("validation", "; ".join(errors))
