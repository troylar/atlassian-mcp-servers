"""Tests for text sanitization utilities."""

from jira_mcp_server.utils.text import (
    escape_jql_value,
    markdown_to_jira,
    sanitize_long_text,
    sanitize_text,
    sanitize_value,
)


class TestSanitizeText:
    def test_passthrough_clean_ascii(self) -> None:
        assert sanitize_text("hello world") == "hello world"

    def test_passthrough_empty_string(self) -> None:
        assert sanitize_text("") == ""

    def test_left_double_smart_quote(self) -> None:
        assert sanitize_text("\u201chello\u201d") == '"hello"'

    def test_right_double_smart_quote(self) -> None:
        assert sanitize_text("say \u201cyes\u201d") == 'say "yes"'

    def test_left_single_smart_quote(self) -> None:
        assert sanitize_text("\u2018hi\u2019") == "'hi'"

    def test_right_single_smart_quote(self) -> None:
        assert sanitize_text("it\u2019s fine") == "it's fine"

    def test_em_dash(self) -> None:
        assert sanitize_text("foo\u2014bar") == "foo-bar"

    def test_en_dash(self) -> None:
        assert sanitize_text("foo\u2013bar") == "foo-bar"

    def test_ellipsis(self) -> None:
        assert sanitize_text("wait\u2026") == "wait..."

    def test_mixed_smart_chars(self) -> None:
        text = "\u201cHello\u201d \u2014 it\u2019s a \u2018test\u2019\u2026"
        expected = '"Hello" - it\'s a \'test\'...'
        assert sanitize_text(text) == expected

    def test_nfc_normalization(self) -> None:
        nfd = "e\u0301"
        result = sanitize_text(nfd)
        assert result == "\u00e9"
        assert len(result) == 1

    def test_preserves_regular_unicode(self) -> None:
        assert sanitize_text("caf\u00e9") == "caf\u00e9"

    def test_preserves_newlines_and_whitespace(self) -> None:
        assert sanitize_text("line1\nline2\ttab") == "line1\nline2\ttab"

    def test_jql_with_smart_quotes(self) -> None:
        jql = 'assignee = f12345 AND resolution = \u201cUnresolved\u201d'
        expected = 'assignee = f12345 AND resolution = "Unresolved"'
        assert sanitize_text(jql) == expected

    def test_inline_code_backticks(self) -> None:
        assert sanitize_text("use `foo` here") == "use {{foo}} here"

    def test_multiple_inline_code(self) -> None:
        assert sanitize_text("`a` and `b`") == "{{a}} and {{b}}"

    def test_stray_backtick_removed(self) -> None:
        assert sanitize_text("it`s broken") == "its broken"

    def test_backtick_at_start_and_end(self) -> None:
        assert sanitize_text("`code`") == "{{code}}"

    def test_mixed_backticks_and_smart_quotes(self) -> None:
        text = "\u201cuse `cmd` here\u201d"
        assert sanitize_text(text) == '"use {{cmd}} here"'

    def test_triple_backtick_stripped(self) -> None:
        assert sanitize_text("```hello```") == "{{hello}}"

    def test_empty_backticks_stripped(self) -> None:
        assert sanitize_text("``") == ""

    def test_no_backticks_passthrough(self) -> None:
        assert sanitize_text("no backticks here") == "no backticks here"

    def test_strip_zero_width_space(self) -> None:
        assert sanitize_text("hello\u200bworld") == "helloworld"

    def test_strip_zero_width_non_joiner(self) -> None:
        assert sanitize_text("hello\u200cworld") == "helloworld"

    def test_strip_zero_width_joiner(self) -> None:
        assert sanitize_text("hello\u200dworld") == "helloworld"

    def test_strip_left_to_right_mark(self) -> None:
        assert sanitize_text("hello\u200eworld") == "helloworld"

    def test_strip_right_to_left_mark(self) -> None:
        assert sanitize_text("hello\u200fworld") == "helloworld"

    def test_strip_byte_order_mark(self) -> None:
        assert sanitize_text("\ufeffhello") == "hello"

    def test_strip_word_joiner(self) -> None:
        assert sanitize_text("hello\u2060world") == "helloworld"

    def test_non_breaking_space_to_space(self) -> None:
        assert sanitize_text("hello\u00a0world") == "hello world"

    def test_strip_null_byte(self) -> None:
        assert sanitize_text("hello\x00world") == "helloworld"

    def test_strip_bell_char(self) -> None:
        assert sanitize_text("hello\x07world") == "helloworld"

    def test_strip_form_feed(self) -> None:
        assert sanitize_text("hello\x0cworld") == "helloworld"

    def test_preserve_newline(self) -> None:
        assert sanitize_text("line1\nline2") == "line1\nline2"

    def test_preserve_tab(self) -> None:
        assert sanitize_text("col1\tcol2") == "col1\tcol2"

    def test_preserve_carriage_return(self) -> None:
        assert sanitize_text("line1\r\nline2") == "line1\r\nline2"

    def test_strip_soft_hyphen(self) -> None:
        assert sanitize_text("auto\u00admatic") == "automatic"

    def test_mixed_invisible_and_smart_chars(self) -> None:
        text = "\ufeff\u201chello\u200b world\u201d"
        assert sanitize_text(text) == '"hello world"'

    def test_strip_multiple_invisible_chars(self) -> None:
        text = "\u200b\u200c\u200d\u200e\u200f\ufeff\u2060"
        assert sanitize_text(text) == ""

    def test_strip_xml_invalid_fffe(self) -> None:
        assert sanitize_text("hello\ufffeworld") == "helloworld"

    def test_strip_xml_invalid_ffff(self) -> None:
        assert sanitize_text("hello\uffffworld") == "helloworld"

    def test_preserve_supplementary_plane_char(self) -> None:
        assert sanitize_text("hello\U0001F600world") == "hello\U0001F600world"

    def test_strip_private_use_area(self) -> None:
        assert sanitize_text("hello\ue000world") == "helloworld"

    def test_strip_private_use_area_high(self) -> None:
        assert sanitize_text("hello\uf8ffworld") == "helloworld"

    def test_preserve_cjk_characters(self) -> None:
        assert sanitize_text("\u4e16\u754c") == "\u4e16\u754c"

    def test_preserve_arabic(self) -> None:
        assert sanitize_text("\u0645\u0631\u062d\u0628\u0627") == "\u0645\u0631\u062d\u0628\u0627"

    def test_strip_c1_control_chars(self) -> None:
        assert sanitize_text("hello\x80world") == "helloworld"
        assert sanitize_text("hello\x9fworld") == "helloworld"


class TestMarkdownToJira:
    def test_passthrough_plain_text(self) -> None:
        assert markdown_to_jira("hello world") == "hello world"

    def test_passthrough_empty_string(self) -> None:
        assert markdown_to_jira("") == ""

    def test_heading_h1(self) -> None:
        assert markdown_to_jira("# Title") == "h1. Title"

    def test_heading_h2(self) -> None:
        assert markdown_to_jira("## Subtitle") == "h2. Subtitle"

    def test_heading_h3(self) -> None:
        assert markdown_to_jira("### Section") == "h3. Section"

    def test_heading_h4(self) -> None:
        assert markdown_to_jira("#### Sub-section") == "h4. Sub-section"

    def test_heading_h5(self) -> None:
        assert markdown_to_jira("##### Small") == "h5. Small"

    def test_heading_h6(self) -> None:
        assert markdown_to_jira("###### Tiny") == "h6. Tiny"

    def test_heading_multiline(self) -> None:
        text = "# First\nsome text\n## Second"
        expected = "h1. First\nsome text\nh2. Second"
        assert markdown_to_jira(text) == expected

    def test_bold(self) -> None:
        assert markdown_to_jira("**bold text**") == "*bold text*"

    def test_bold_in_sentence(self) -> None:
        assert markdown_to_jira("this is **important** stuff") == "this is *important* stuff"

    def test_multiple_bold(self) -> None:
        assert markdown_to_jira("**a** and **b**") == "*a* and *b*"

    def test_italic_star(self) -> None:
        assert markdown_to_jira("*italic text*") == "_italic text_"

    def test_italic_star_in_sentence(self) -> None:
        assert markdown_to_jira("this is *emphasized* here") == "this is _emphasized_ here"

    def test_strikethrough(self) -> None:
        assert markdown_to_jira("~~deleted~~") == "-deleted-"

    def test_strikethrough_in_sentence(self) -> None:
        assert markdown_to_jira("this is ~~wrong~~ right") == "this is -wrong- right"

    def test_link(self) -> None:
        assert markdown_to_jira("[Google](https://google.com)") == "[Google|https://google.com]"

    def test_link_in_sentence(self) -> None:
        text = "Visit [the docs](https://docs.example.com) for more"
        expected = "Visit [the docs|https://docs.example.com] for more"
        assert markdown_to_jira(text) == expected

    def test_multiple_links(self) -> None:
        text = "[a](http://a.com) and [b](http://b.com)"
        expected = "[a|http://a.com] and [b|http://b.com]"
        assert markdown_to_jira(text) == expected

    def test_image(self) -> None:
        assert markdown_to_jira("![alt](image.png)") == "!image.png!"

    def test_image_with_url(self) -> None:
        assert markdown_to_jira("![screenshot](https://example.com/img.png)") == "!https://example.com/img.png!"

    def test_bullet_list_dash(self) -> None:
        text = "- item one\n- item two"
        expected = "* item one\n* item two"
        assert markdown_to_jira(text) == expected

    def test_bullet_list_star(self) -> None:
        text = "* item one\n* item two"
        expected = "* item one\n* item two"
        assert markdown_to_jira(text) == expected

    def test_numbered_list(self) -> None:
        text = "1. first\n2. second\n3. third"
        expected = "# first\n# second\n# third"
        assert markdown_to_jira(text) == expected

    def test_horizontal_rule_dashes(self) -> None:
        assert markdown_to_jira("---") == "----"

    def test_horizontal_rule_long(self) -> None:
        assert markdown_to_jira("-----") == "----"

    def test_horizontal_rule_stars(self) -> None:
        assert markdown_to_jira("***") == "----"

    def test_fenced_code_block_no_lang(self) -> None:
        text = "```\nprint('hello')\n```"
        expected = "{code}\nprint('hello')\n{code}"
        assert markdown_to_jira(text) == expected

    def test_fenced_code_block_with_lang(self) -> None:
        text = "```python\ndef foo():\n    pass\n```"
        expected = "{code:python}\ndef foo():\n    pass\n{code}"
        assert markdown_to_jira(text) == expected

    def test_fenced_code_block_java(self) -> None:
        text = "```java\nSystem.out.println();\n```"
        expected = "{code:java}\nSystem.out.println();\n{code}"
        assert markdown_to_jira(text) == expected

    def test_multiple_code_blocks(self) -> None:
        text = "```\nfoo\n```\ntext\n```\nbar\n```"
        expected = "{code}\nfoo\n{code}\ntext\n{code}\nbar\n{code}"
        assert markdown_to_jira(text) == expected

    def test_code_block_content_not_converted(self) -> None:
        text = "```\n# not a heading\n**not bold**\n```"
        expected = "{code}\n# not a heading\n**not bold**\n{code}"
        assert markdown_to_jira(text) == expected

    def test_lone_brace_stripped(self) -> None:
        assert markdown_to_jira("use { and }") == "use  and "

    def test_jira_inline_code_preserved(self) -> None:
        assert markdown_to_jira("use {{foo}} here") == "use {{foo}} here"

    def test_jira_code_macro_preserved(self) -> None:
        text = "{code}\nsome code\n{code}"
        assert markdown_to_jira(text) == text

    def test_mixed_formatting(self) -> None:
        text = "# Header\n\n**Bold** and *italic* text\n\n- item 1\n- item 2\n\n[link](http://example.com)"
        expected = "h1. Header\n\n*Bold* and _italic_ text\n\n* item 1\n* item 2\n\n[link|http://example.com]"
        assert markdown_to_jira(text) == expected

    def test_bold_inside_heading(self) -> None:
        assert markdown_to_jira("## **Important** Section") == "h2. *Important* Section"

    def test_link_inside_bullet(self) -> None:
        text = "- [docs](http://docs.com)"
        expected = "* [docs|http://docs.com]"
        assert markdown_to_jira(text) == expected

    def test_hash_not_heading_mid_line(self) -> None:
        assert markdown_to_jira("issue #123") == "issue #123"

    def test_star_not_bold_single(self) -> None:
        assert markdown_to_jira("a * b * c") == "a * b * c"

    def test_preserves_plain_text_with_numbers(self) -> None:
        assert markdown_to_jira("there are 3 items") == "there are 3 items"

    def test_numbered_mid_line_not_converted(self) -> None:
        assert markdown_to_jira("step 1. do this") == "step 1. do this"

    def test_realistic_mcp_description(self) -> None:
        text = (
            "## Summary\n\n"
            "This issue tracks **critical** bugs in the login module.\n\n"
            "### Steps to Reproduce\n\n"
            "1. Go to [login page](https://app.example.com/login)\n"
            "2. Enter *invalid* credentials\n"
            "3. Click submit\n\n"
            "### Expected\n\n"
            "- Show error message\n"
            "- Keep form data\n\n"
            "```python\ndef test():\n    assert True\n```"
        )
        expected = (
            "h2. Summary\n\n"
            "This issue tracks *critical* bugs in the login module.\n\n"
            "h3. Steps to Reproduce\n\n"
            "# Go to [login page|https://app.example.com/login]\n"
            "# Enter _invalid_ credentials\n"
            "# Click submit\n\n"
            "h3. Expected\n\n"
            "* Show error message\n"
            "* Keep form data\n\n"
            "{code:python}\ndef test():\n    assert True\n{code}"
        )
        assert markdown_to_jira(text) == expected


class TestSanitizeLongText:
    def test_passthrough_plain_text(self) -> None:
        assert sanitize_long_text("hello world") == "hello world"

    def test_passthrough_empty_string(self) -> None:
        assert sanitize_long_text("") == ""

    def test_smart_quotes_then_markdown(self) -> None:
        text = "\u201c**bold**\u201d"
        expected = '"*bold*"'
        assert sanitize_long_text(text) == expected

    def test_backticks_converted_before_markdown(self) -> None:
        text = "use `code` and **bold**"
        expected = "use {{code}} and *bold*"
        assert sanitize_long_text(text) == expected

    def test_full_chain(self) -> None:
        text = "## \u201cHeader\u201d\n\n- `item` one\n- **two**"
        expected = 'h2. "Header"\n\n* {{item}} one\n* *two*'
        assert sanitize_long_text(text) == expected

    def test_em_dash_and_heading(self) -> None:
        text = "# Title \u2014 Subtitle"
        expected = "h1. Title - Subtitle"
        assert sanitize_long_text(text) == expected

    def test_fenced_code_block_preserved(self) -> None:
        text = "```python\ndef foo():\n    pass\n```"
        expected = "{code:python}\ndef foo():\n    pass\n{code}"
        assert sanitize_long_text(text) == expected

    def test_fenced_code_block_with_surrounding_text(self) -> None:
        text = "## Example\n\n```python\ndef foo():\n    pass\n```\n\nDone."
        expected = "h2. Example\n\n{code:python}\ndef foo():\n    pass\n{code}\n\nDone."
        assert sanitize_long_text(text) == expected

    def test_inline_code_and_fenced_block(self) -> None:
        text = "Use `foo` like:\n\n```python\nfoo()\n```"
        expected = "Use {{foo}} like:\n\n{code:python}\nfoo()\n{code}"
        assert sanitize_long_text(text) == expected

    def test_invisible_chars_stripped_in_long_text(self) -> None:
        text = "hello\u200b\ufeff world"
        assert sanitize_long_text(text) == "hello world"


class TestSanitizeValue:
    def test_string_sanitized(self) -> None:
        assert sanitize_value("\u201chello\u201d") == '"hello"'

    def test_int_passthrough(self) -> None:
        assert sanitize_value(42) == 42

    def test_float_passthrough(self) -> None:
        assert sanitize_value(3.14) == 3.14

    def test_bool_passthrough(self) -> None:
        assert sanitize_value(True) is True

    def test_none_passthrough(self) -> None:
        assert sanitize_value(None) is None

    def test_dict_string_values_sanitized(self) -> None:
        result = sanitize_value({"name": "\u201ctest\u201d", "count": 5})
        assert result == {"name": '"test"', "count": 5}

    def test_list_string_values_sanitized(self) -> None:
        result = sanitize_value(["\u201ca\u201d", 1, "\u2018b\u2019"])
        assert result == ['"a"', 1, "'b'"]

    def test_nested_dict_sanitized(self) -> None:
        result = sanitize_value({"outer": {"inner": "\u2014dash"}})
        assert result == {"outer": {"inner": "-dash"}}

    def test_list_of_dicts_sanitized(self) -> None:
        result = sanitize_value([{"value": "\u2026"}, {"value": "ok"}])
        assert result == [{"value": "..."}, {"value": "ok"}]

    def test_empty_dict(self) -> None:
        assert sanitize_value({}) == {}

    def test_empty_list(self) -> None:
        assert sanitize_value([]) == []

    def test_empty_string(self) -> None:
        assert sanitize_value("") == ""


class TestEscapeJqlValue:
    def test_simple_value(self) -> None:
        assert escape_jql_value("In Progress") == '"In Progress"'

    def test_empty_value(self) -> None:
        assert escape_jql_value("") == '""'

    def test_value_with_double_quote(self) -> None:
        assert escape_jql_value('say "hello"') == '"say \\"hello\\""'

    def test_value_with_backslash(self) -> None:
        assert escape_jql_value("path\\to") == '"path\\\\to"'

    def test_value_with_backslash_and_quote(self) -> None:
        assert escape_jql_value('a\\"b') == '"a\\\\\\"b"'

    def test_smart_quotes_replaced_then_escaped(self) -> None:
        assert escape_jql_value("\u201chello\u201d") == '"\\"hello\\""'

    def test_em_dash_replaced(self) -> None:
        assert escape_jql_value("foo\u2014bar") == '"foo-bar"'

    def test_nfc_normalization(self) -> None:
        result = escape_jql_value("e\u0301")
        assert result == '"\u00e9"'

    def test_passthrough_clean_value(self) -> None:
        assert escape_jql_value("bug") == '"bug"'

    def test_label_with_special_chars(self) -> None:
        assert escape_jql_value("feature-docs") == '"feature-docs"'

    def test_injection_attempt_with_quote(self) -> None:
        malicious = 'bug" OR priority = "High'
        result = escape_jql_value(malicious)
        assert result == '"bug\\" OR priority = \\"High"'
