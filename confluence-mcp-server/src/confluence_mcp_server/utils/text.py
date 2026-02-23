"""Markdown to Confluence storage format (XHTML) converter.

Uses mistune to parse markdown and a custom renderer to emit Confluence
storage-format XHTML. Code blocks are rendered as <ac:structured-macro>
elements with CDATA-wrapped bodies.
"""

from typing import Any, Optional
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

import mistune
from mistune import HTMLRenderer

_DANGEROUS_SCHEMES = frozenset({"javascript", "data", "vbscript"})


class ConfluenceStorageRenderer(HTMLRenderer):
    """Renders markdown tokens as Confluence storage-format XHTML.

    Most HTML output from the base HTMLRenderer is already valid Confluence
    storage format. This subclass overrides only the methods that need
    Confluence-specific XML elements (code blocks) or adjusted output.
    """

    def block_code(self, code: str, info: Optional[str] = None) -> str:
        """Render fenced code blocks as Confluence code macros.

        Produces <ac:structured-macro ac:name="code"> with a CDATA-wrapped
        plain-text-body. The CDATA terminator ]]> is escaped to prevent
        injection.
        """
        params = ""
        if info is not None:
            lang = info.strip().split(None, 1)[0] if info.strip() else ""
            if lang:
                params = f'<ac:parameter ac:name="language">{xml_escape(lang)}</ac:parameter>'

        safe_code = code.replace("]]>", "]]]]><![CDATA[>")
        return (
            f'<ac:structured-macro ac:name="code">'
            f"{params}"
            f"<ac:plain-text-body><![CDATA[{safe_code}]]></ac:plain-text-body>"
            f"</ac:structured-macro>\n"
        )

    def heading(self, text: str, level: int, **attrs: Any) -> str:
        tag = "h" + str(level)
        return f"<{tag}>{text}</{tag}>\n"

    def thematic_break(self) -> str:
        return "<hr/>\n"

    def image(self, text: str, url: str, title: Optional[str] = None) -> str:
        return f'<ac:image><ri:url ri:value="{xml_escape(url)}"/></ac:image>'

    def block_quote(self, text: str) -> str:
        return f"<blockquote>{text}</blockquote>\n"

    def link(self, text: str, url: str, title: Optional[str] = None) -> str:
        """Render links with dangerous URI scheme rejection."""
        if url:
            parsed = urlparse(url.strip())
            if parsed.scheme.lower() in _DANGEROUS_SCHEMES:
                return xml_escape(text)
        safe_url = xml_escape(url)
        if title:
            return f'<a href="{safe_url}" title="{xml_escape(title)}">{text}</a>'
        return f'<a href="{safe_url}">{text}</a>'


def _make_confluence_markdown() -> mistune.Markdown:
    """Create a configured mistune Markdown instance with Confluence renderer."""
    renderer = ConfluenceStorageRenderer(escape=True)
    return mistune.create_markdown(
        renderer=renderer,
        plugins=["table", "strikethrough"],
    )


_md = _make_confluence_markdown()


def markdown_to_storage(text: str) -> str:
    """Convert markdown text to Confluence storage format (XHTML).

    Uses mistune to parse markdown and a custom renderer to produce
    Confluence-compatible XHTML. Code blocks become <ac:structured-macro>
    elements. Most other HTML elements are natively valid in Confluence
    storage format.

    Args:
        text: Markdown-formatted text to convert.

    Returns:
        Confluence storage format XHTML string.
    """
    if not text:
        return ""
    result = str(_md(text))
    return result
