"""Text sanitization utilities for Jira API compatibility."""

import re
import unicodedata

SMART_CHAR_MAP = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
    }
)

_INLINE_CODE_RE = re.compile(r"`([^`]+)`")


def sanitize_text(text: str) -> str:
    """Normalize unicode and replace smart quotes/dashes with ASCII equivalents.

    MCP clients often send smart/curly quotes and other unicode characters
    that Jira's REST API rejects. This function normalizes text to prevent
    'disallowed characters' errors.

    Also converts markdown inline code (backticks) to Jira wiki markup,
    since Jira rejects backtick characters.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.translate(SMART_CHAR_MAP)
    text = _INLINE_CODE_RE.sub(r"{{\1}}", text)
    text = text.replace("`", "")
    return text


def escape_jql_value(value: str) -> str:
    """Sanitize and escape a value for safe interpolation into a JQL query.

    Returns the value wrapped in double quotes with internal quotes and
    backslashes escaped. The caller should NOT add surrounding quotes.
    """
    value = sanitize_text(value)
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{value}"'
