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
        "\u00a0": " ",  # non-breaking space → regular space
    }
)

_ALLOWED_CONTROL_CHARS = frozenset("\n\r\t")

_INLINE_CODE_RE = re.compile(r"`([^`]+)`")

_MD_FENCED_CODE_RE = re.compile(r"^```(\w*)\n(.*?)^```", re.MULTILINE | re.DOTALL)
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_STAR_RE = re.compile(r"(?<!\*)\*(?!\*|\s)(.+?)(?<!\*|\s)\*(?!\*)")
_MD_STRIKETHROUGH_RE = re.compile(r"~~(.+?)~~")
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MD_BULLET_RE = re.compile(r"^[-*]\s+", re.MULTILINE)
_MD_NUMBERED_RE = re.compile(r"^\d+\.\s+", re.MULTILINE)
_MD_HR_RE = re.compile(r"^[-*]{3,}\s*$", re.MULTILINE)

_JIRA_BRACE_PATTERN_RE = re.compile(
    r"\{\{.+?\}\}"  # {{inline code}}
    r"|\{code(?::\w+)?\}.*?\{code\}"  # {code}...{code} or {code:lang}...{code}
    r"|\{quote\}.*?\{quote\}"  # {quote}...{quote}
    r"|\{noformat\}.*?\{noformat\}",  # {noformat}...{noformat}
    re.DOTALL,
)

_CODE_PLACEHOLDER = "\x00CODE_BLOCK_{}\x00"
_BOLD_PLACEHOLDER = "\x00BOLD_{}\x00"


def _strip_invisible_chars(text: str) -> str:
    """Strip invisible Unicode characters that Jira's REST API rejects.

    Removes:
    - Control characters (category Cc) except newline, carriage return, tab
    - Format characters (category Cf) — zero-width spaces, BOM, directional marks
    """
    result: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat == "Cc" and ch not in _ALLOWED_CONTROL_CHARS:
            continue
        if cat == "Cf":
            continue
        result.append(ch)
    return "".join(result)


def sanitize_text(text: str) -> str:
    """Normalize unicode and replace smart quotes/dashes with ASCII equivalents.

    MCP clients often send smart/curly quotes, invisible Unicode characters,
    and other characters that Jira's REST API rejects. This function normalizes
    text to prevent 'disallowed characters' errors.

    Strips: control chars, zero-width chars, BOM, directional marks.
    Replaces: smart quotes, em/en dashes, ellipsis, non-breaking spaces.
    Converts: markdown inline code (backticks) to Jira wiki markup {{...}}.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.translate(SMART_CHAR_MAP)
    text = _strip_invisible_chars(text)
    text = _INLINE_CODE_RE.sub(r"{{\1}}", text)
    text = text.replace("`", "")
    return text


def _replace_fenced_code(match: re.Match[str]) -> str:
    lang = match.group(1)
    code = match.group(2)
    if code.endswith("\n"):
        code = code[:-1]
    if lang:
        return f"{{code:{lang}}}\n{code}\n{{code}}"
    return f"{{code}}\n{code}\n{{code}}"


def _replace_heading(match: re.Match[str]) -> str:
    level = len(match.group(1))
    text = match.group(2)
    return f"h{level}. {text}"


def _escape_lone_braces(text: str) -> str:
    """Strip { and } that are not part of Jira macros or inline code markup.

    Preserves {{inline}}, {code}...{code}, {code:lang}...{code},
    {quote}...{quote}, and {noformat}...{noformat} patterns.
    Strips all other lone braces.
    """
    protected: list[tuple[int, int]] = []
    for match in _JIRA_BRACE_PATTERN_RE.finditer(text):
        protected.append((match.start(), match.end()))

    result: list[str] = []
    i = 0
    for start, end in protected:
        for j in range(i, start):
            ch = text[j]
            if ch not in "{}":
                result.append(ch)
        result.append(text[start:end])
        i = end
    for j in range(i, len(text)):
        ch = text[j]
        if ch not in "{}":
            result.append(ch)
    return "".join(result)


def markdown_to_jira(text: str) -> str:
    """Convert markdown formatting to Jira wiki markup.

    Handles headings, bold, italic, strikethrough, links, images,
    bullet lists, numbered lists, fenced code blocks, and horizontal rules.

    Lone curly braces that would trigger Jira macro parsing are stripped.
    """
    if not text:
        return text

    code_blocks: list[str] = []

    def _extract_code(match: re.Match[str]) -> str:
        replacement = _replace_fenced_code(match)
        idx = len(code_blocks)
        code_blocks.append(replacement)
        return _CODE_PLACEHOLDER.format(idx)

    text = _MD_FENCED_CODE_RE.sub(_extract_code, text)

    text = _MD_HEADING_RE.sub(_replace_heading, text)

    bold_parts: list[str] = []

    def _extract_bold(match: re.Match[str]) -> str:
        jira_bold = f"*{match.group(1)}*"
        idx = len(bold_parts)
        bold_parts.append(jira_bold)
        return _BOLD_PLACEHOLDER.format(idx)

    text = _MD_BOLD_RE.sub(_extract_bold, text)

    text = _MD_ITALIC_STAR_RE.sub(r"_\1_", text)

    for idx, val in enumerate(bold_parts):
        text = text.replace(_BOLD_PLACEHOLDER.format(idx), val)

    text = _MD_STRIKETHROUGH_RE.sub(r"-\1-", text)

    text = _MD_IMAGE_RE.sub(r"!\2!", text)
    text = _MD_LINK_RE.sub(r"[\1|\2]", text)

    text = _MD_BULLET_RE.sub("* ", text)
    text = _MD_NUMBERED_RE.sub("# ", text)

    text = _MD_HR_RE.sub("----", text)

    text = _escape_lone_braces(text)

    for idx, block in enumerate(code_blocks):
        text = text.replace(_CODE_PLACEHOLDER.format(idx), block)

    return text


def sanitize_long_text(text: str) -> str:
    """Sanitize long-form text fields (descriptions, comments).

    Chains sanitize_text (unicode normalization, smart quotes, inline code)
    with markdown_to_jira (full markdown-to-wiki-markup conversion).

    Use this for description and comment body fields. Use sanitize_text()
    for short fields like summary, labels, and filter names.
    """
    text = sanitize_text(text)
    text = markdown_to_jira(text)
    return text


def escape_jql_value(value: str) -> str:
    """Sanitize and escape a value for safe interpolation into a JQL query.

    Returns the value wrapped in double quotes with internal quotes and
    backslashes escaped. The caller should NOT add surrounding quotes.
    """
    value = sanitize_text(value)
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{value}"'
