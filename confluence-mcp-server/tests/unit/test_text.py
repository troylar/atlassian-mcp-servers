"""Tests for confluence_mcp_server.utils.text — markdown to storage format."""

import pytest

from confluence_mcp_server.utils.text import (
    ConfluenceStorageRenderer,
    _make_confluence_markdown,
    markdown_to_storage,
)


class TestMarkdownToStorage:
    """Tests for the markdown_to_storage public function."""

    def test_empty_string(self) -> None:
        assert markdown_to_storage("") == ""

    def test_plain_paragraph(self) -> None:
        assert markdown_to_storage("hello world") == "<p>hello world</p>\n"

    def test_two_paragraphs(self) -> None:
        result = markdown_to_storage("line1\n\nline2")
        assert "<p>line1</p>" in result
        assert "<p>line2</p>" in result

    def test_bold(self) -> None:
        result = markdown_to_storage("**bold**")
        assert "<strong>bold</strong>" in result

    def test_italic(self) -> None:
        result = markdown_to_storage("*italic*")
        assert "<em>italic</em>" in result

    def test_bold_italic(self) -> None:
        result = markdown_to_storage("***bold italic***")
        assert "<strong>bold italic</strong>" in result
        assert "<em>" in result

    def test_inline_code(self) -> None:
        result = markdown_to_storage("`code`")
        assert "<code>code</code>" in result

    def test_link(self) -> None:
        result = markdown_to_storage("[click](https://example.com)")
        assert '<a href="https://example.com">click</a>' in result

    def test_link_javascript_rejected(self) -> None:
        result = markdown_to_storage("[click](javascript:alert(1))")
        assert "javascript:" not in result
        assert "click" in result

    def test_link_with_title(self) -> None:
        result = markdown_to_storage('[click](https://example.com "My Title")')
        assert 'title="My Title"' in result
        assert 'href="https://example.com"' in result

    def test_image(self) -> None:
        result = markdown_to_storage("![alt](https://img.example.com/pic.png)")
        assert '<ac:image><ri:url ri:value="https://img.example.com/pic.png"/></ac:image>' in result

    def test_image_url_escaped(self) -> None:
        result = markdown_to_storage("![alt](https://example.com/a&b)")
        assert "ri:value=" in result
        assert "&amp;" in result

    def test_heading_1(self) -> None:
        assert markdown_to_storage("# H1") == "<h1>H1</h1>\n"

    def test_heading_2(self) -> None:
        assert markdown_to_storage("## H2") == "<h2>H2</h2>\n"

    def test_heading_3(self) -> None:
        assert markdown_to_storage("### H3") == "<h3>H3</h3>\n"

    def test_heading_6(self) -> None:
        assert markdown_to_storage("###### H6") == "<h6>H6</h6>\n"

    def test_unordered_list(self) -> None:
        result = markdown_to_storage("- a\n- b")
        assert "<ul>" in result
        assert "<li>" in result
        assert "a" in result
        assert "b" in result

    def test_ordered_list(self) -> None:
        result = markdown_to_storage("1. first\n2. second")
        assert "<ol>" in result
        assert "<li>" in result

    def test_blockquote(self) -> None:
        result = markdown_to_storage("> quoted")
        assert "<blockquote>" in result
        assert "quoted" in result

    def test_thematic_break(self) -> None:
        result = markdown_to_storage("---")
        assert "<hr/>" in result

    def test_strikethrough(self) -> None:
        result = markdown_to_storage("~~deleted~~")
        assert "<del>deleted</del>" in result

    def test_table(self) -> None:
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = markdown_to_storage(md)
        assert "<table>" in result
        assert "<thead>" in result
        assert "<tbody>" in result
        assert "<th>" in result
        assert "<td>" in result

    def test_fenced_code_with_language(self) -> None:
        md = "```python\nprint('hi')\n```"
        result = markdown_to_storage(md)
        assert '<ac:structured-macro ac:name="code">' in result
        assert '<ac:parameter ac:name="language">python</ac:parameter>' in result
        assert "<![CDATA[print('hi')\n]]>" in result
        assert "</ac:structured-macro>" in result

    def test_fenced_code_without_language(self) -> None:
        md = "```\nsome code\n```"
        result = markdown_to_storage(md)
        assert '<ac:structured-macro ac:name="code">' in result
        assert "ac:parameter" not in result
        assert "<![CDATA[some code\n]]>" in result

    def test_fenced_code_cdata_escape(self) -> None:
        md = "```\nif (a]]>b) { }\n```"
        result = markdown_to_storage(md)
        assert "]]]]><![CDATA[>" in result
        assert "]]>b" not in result

    def test_fenced_code_language_xml_escaped(self) -> None:
        md = '```a<b\ncode\n```'
        result = markdown_to_storage(md)
        assert "a&lt;b" in result

    def test_html_entities_escaped(self) -> None:
        result = markdown_to_storage("a & b < c")
        assert "&amp;" in result
        assert "&lt;" in result

    def test_complex_document(self) -> None:
        md = (
            "# Title\n\n"
            "A paragraph with **bold** and *italic*.\n\n"
            "```python\ndef f():\n    pass\n```\n\n"
            "- item 1\n- item 2\n"
        )
        result = markdown_to_storage(md)
        assert "<h1>Title</h1>" in result
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result
        assert '<ac:structured-macro ac:name="code">' in result
        assert "<ul>" in result


class TestConfluenceStorageRenderer:
    """Direct tests for the renderer methods."""

    @pytest.fixture()
    def renderer(self) -> ConfluenceStorageRenderer:
        return ConfluenceStorageRenderer(escape=True)

    def test_block_code_no_info(self, renderer: ConfluenceStorageRenderer) -> None:
        result = renderer.block_code("x = 1\n")
        assert '<ac:structured-macro ac:name="code">' in result
        assert "ac:parameter" not in result
        assert "<![CDATA[x = 1\n]]>" in result

    def test_block_code_with_info(self, renderer: ConfluenceStorageRenderer) -> None:
        result = renderer.block_code("x = 1\n", info="python")
        assert '<ac:parameter ac:name="language">python</ac:parameter>' in result

    def test_block_code_info_with_extra(self, renderer: ConfluenceStorageRenderer) -> None:
        result = renderer.block_code("code\n", info="js extra-stuff")
        assert '<ac:parameter ac:name="language">js</ac:parameter>' in result

    def test_block_code_info_empty_string(self, renderer: ConfluenceStorageRenderer) -> None:
        result = renderer.block_code("code\n", info="")
        assert "ac:parameter" not in result

    def test_block_code_info_whitespace_only(self, renderer: ConfluenceStorageRenderer) -> None:
        result = renderer.block_code("code\n", info="   ")
        assert "ac:parameter" not in result

    def test_heading_levels(self, renderer: ConfluenceStorageRenderer) -> None:
        for level in range(1, 7):
            result = renderer.heading("text", level)
            assert result == f"<h{level}>text</h{level}>\n"

    def test_thematic_break(self, renderer: ConfluenceStorageRenderer) -> None:
        assert renderer.thematic_break() == "<hr/>\n"

    def test_image_basic(self, renderer: ConfluenceStorageRenderer) -> None:
        result = renderer.image("alt", "https://example.com/img.png")
        assert '<ac:image><ri:url ri:value="https://example.com/img.png"/></ac:image>' == result

    def test_image_url_with_ampersand(self, renderer: ConfluenceStorageRenderer) -> None:
        result = renderer.image("alt", "https://example.com/img?a=1&b=2")
        assert "&amp;" in result

    def test_block_quote(self, renderer: ConfluenceStorageRenderer) -> None:
        assert renderer.block_quote("<p>text</p>") == "<blockquote><p>text</p></blockquote>\n"


class TestMakeConfluenceMarkdown:
    """Tests for the factory function."""

    def test_returns_callable(self) -> None:
        md = _make_confluence_markdown()
        assert callable(md)

    def test_produces_html(self) -> None:
        md = _make_confluence_markdown()
        result = md("hello")
        assert "<p>hello</p>" in result
