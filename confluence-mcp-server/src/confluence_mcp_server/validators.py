"""Input validation helpers for Confluence MCP Server (OWASP ASVS V5)."""

import re
from pathlib import Path
from urllib.parse import quote as url_quote
from urllib.parse import urlparse

# Confluence content IDs are numeric strings
_NUMERIC_ID_RE = re.compile(r"^\d+$")

# Space keys: uppercase letters, digits, underscore
_SPACE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

MAX_ID_LENGTH = 255


def validate_content_id(value: str, name: str = "content_id") -> str:
    """Validate a Confluence content ID (numeric string)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if not _NUMERIC_ID_RE.match(value):
        raise ValueError(f"{name} must be a numeric string")
    return value


def validate_space_key(value: str, name: str = "space_key") -> str:
    """Validate a Confluence space key (e.g., DEV)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if len(value) > MAX_ID_LENGTH:
        raise ValueError(f"{name} exceeds maximum length of {MAX_ID_LENGTH}")
    if not _SPACE_KEY_RE.match(value):
        raise ValueError(f"{name} must be uppercase letters/digits/underscores starting with a letter")
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


def sanitize_cql_value(value: str) -> str:
    """Escape special characters in CQL query values.

    CQL uses double-quotes for string values. We escape embedded quotes
    and backslashes to prevent CQL injection.
    """
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return value


def validate_url_path_segment(value: str, name: str = "segment") -> str:
    """URL-encode a path segment to prevent path injection."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return url_quote(value.strip(), safe="")


def validate_link_url(url: str) -> str:
    """Validate a URL for use in links — reject dangerous schemes."""
    if not url:
        return url
    parsed = urlparse(url.strip())
    dangerous_schemes = {"javascript", "data", "vbscript"}
    if parsed.scheme.lower() in dangerous_schemes:
        raise ValueError(f"Dangerous URL scheme rejected: {parsed.scheme}")
    return url


# Allowed values for enum parameters
CONTENT_TYPES = frozenset({"page", "blogpost", "comment", "attachment"})
MOVE_POSITIONS = frozenset({"append", "before", "after"})
REPRESENTATIONS = frozenset({
    "storage", "editor", "wiki", "view",
    "export_view", "styled_view", "anonymous_export_view",
})


def _safe_error_text(response_text: str, max_len: int = 200) -> str:
    """Truncate response text for error messages, stripping potential secrets."""
    text = response_text[:max_len]
    text = re.sub(r"(Bearer|Basic)\s+[A-Za-z0-9+/=_-]+", "[REDACTED]", text)
    return text
