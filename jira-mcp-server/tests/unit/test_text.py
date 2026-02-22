"""Tests for text sanitization utilities."""

from jira_mcp_server.utils.text import escape_jql_value, sanitize_text


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
        # e + combining acute accent (NFD) should normalize to single char (NFC)
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
        # Smart quotes become straight quotes, then get escaped
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
        # Attempting JQL injection via a label containing "
        malicious = 'bug" OR priority = "High'
        result = escape_jql_value(malicious)
        assert result == '"bug\\" OR priority = \\"High"'
