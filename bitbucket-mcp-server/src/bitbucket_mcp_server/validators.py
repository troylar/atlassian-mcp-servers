"""Input validation helpers for Bitbucket MCP Server (OWASP ASVS V5)."""

import re
from urllib.parse import quote as url_quote
from urllib.parse import urlparse

# Project keys (DC): uppercase alpha + digits
_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

# Repo slugs: lowercase alphanumeric, hyphens, underscores, dots
_REPO_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")

# Git ref names: no space, no .., no control chars, no ~^:?\[
_GIT_REF_RE = re.compile(r"^[^\x00-\x1f ~^:?*\[\\]+$")

# Commit hashes: 4-40 hex chars (short or full SHA)
_COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")

# Numeric IDs (webhook IDs, comment IDs)
_NUMERIC_ID_RE = re.compile(r"^\d+$")

MAX_ID_LENGTH = 255

# Private/reserved IP ranges for SSRF prevention
_PRIVATE_IP_PATTERNS = [
    re.compile(r"^127\."),
    re.compile(r"^10\."),
    re.compile(r"^172\.(1[6-9]|2\d|3[01])\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^169\.254\."),
    re.compile(r"^0\."),
]


def validate_project_key(value: str, name: str = "project") -> str:
    """Validate a Bitbucket project key."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if len(value) > MAX_ID_LENGTH:
        raise ValueError(f"{name} exceeds maximum length of {MAX_ID_LENGTH}")
    if not _PROJECT_KEY_RE.match(value):
        raise ValueError(f"{name} must be uppercase letters/digits/underscores starting with a letter")
    return value


def validate_repo_slug(value: str, name: str = "repo") -> str:
    """Validate a Bitbucket repository slug."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if len(value) > MAX_ID_LENGTH:
        raise ValueError(f"{name} exceeds maximum length of {MAX_ID_LENGTH}")
    if not _REPO_SLUG_RE.match(value):
        raise ValueError(f"{name} must be alphanumeric with hyphens/underscores/dots")
    return value


def validate_git_ref(value: str, name: str = "ref") -> str:
    """Validate a git ref name (branch, tag)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if len(value) > MAX_ID_LENGTH:
        raise ValueError(f"{name} exceeds maximum length of {MAX_ID_LENGTH}")
    if ".." in value:
        raise ValueError(f"{name} must not contain '..'")
    if not _GIT_REF_RE.match(value):
        raise ValueError(f"{name} contains invalid characters for a git ref")
    return value


def validate_commit_hash(value: str, name: str = "commit_id") -> str:
    """Validate a git commit hash (short or full SHA)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if not _COMMIT_HASH_RE.match(value):
        raise ValueError(f"{name} must be a valid hex commit hash (4-40 characters)")
    return value


def validate_numeric_id(value: str, name: str = "id") -> str:
    """Validate a numeric ID string."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    if not _NUMERIC_ID_RE.match(value):
        raise ValueError(f"{name} must be a numeric string")
    return value


def validate_positive_int(value: int, name: str = "id") -> int:
    """Validate a positive integer (PR IDs, comment IDs)."""
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def validate_max_results(value: int, ceiling: int = 100) -> int:
    """Cap max_results to a safe ceiling."""
    if value < 0:
        raise ValueError("max_results must not be negative")
    return min(value, ceiling)


def validate_url(value: str, name: str = "url") -> str:
    """Validate a URL for webhook/build status — reject SSRF targets.

    Only allows http:// and https:// schemes. Rejects private IPs,
    localhost, and dangerous schemes (file://, javascript:, etc.).
    """
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    value = value.strip()
    parsed = urlparse(value)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{name} must use http:// or https:// scheme")

    hostname = parsed.hostname or ""

    if not hostname:
        raise ValueError(f"{name} must have a valid hostname")

    # Reject localhost variants
    if hostname in ("localhost", "0.0.0.0", "::1", "[::1]"):
        raise ValueError(f"{name} must not target localhost")

    # Reject private IP ranges
    for pattern in _PRIVATE_IP_PATTERNS:
        if pattern.match(hostname):
            raise ValueError(f"{name} must not target private IP addresses")

    return value


def validate_enum(value: str, name: str, allowed: frozenset[str]) -> str:
    """Validate that a value is in an allowed set (case-insensitive)."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    normalized = value.strip().upper()
    allowed_upper = {v.upper() for v in allowed}
    if normalized not in allowed_upper:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}")
    for v in allowed:
        if v.upper() == normalized:
            return v
    return value  # pragma: no cover


def validate_url_path_segment(value: str, name: str = "segment") -> str:
    """URL-encode a path segment to prevent path injection."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return url_quote(value.strip(), safe="")


def validate_file_path(value: str, name: str = "path") -> str:
    """Validate a file path for browsing/content retrieval.

    Rejects path traversal attempts.
    """
    if ".." in value.split("/"):
        raise ValueError(f"{name} must not contain '..' path traversal")
    return value


# Allowed values for enum parameters
PR_STATES = frozenset({"OPEN", "MERGED", "DECLINED", "ALL"})
BUILD_STATES = frozenset({"SUCCESSFUL", "FAILED", "INPROGRESS"})


def _safe_error_text(response_text: str, max_len: int = 200) -> str:
    """Truncate response text for error messages, stripping potential secrets."""
    text = response_text[:max_len]
    text = re.sub(r"(Bearer|Basic)\s+[A-Za-z0-9+/=_-]+", "[REDACTED]", text)
    return text
