"""Tests for response formatters."""

from unittest.mock import MagicMock

import pytest

from confluence_mcp_server.formatters import (
    _extract_body_text,
    _extract_name,
    _links,
    _max_desc,
    _resolve_detail,
    format_attachment,
    format_attachments,
    format_comment,
    format_comments,
    format_label,
    format_labels,
    format_page,
    format_pages,
    format_search_result,
    format_search_results,
    format_space,
    format_spaces,
    format_user,
    truncate_text,
)


def _make_config(
    default_detail: str = "summary",
    max_description_length: int = 500,
    include_links: bool = False,
) -> MagicMock:
    config = MagicMock()
    config.default_detail = default_detail
    config.max_description_length = max_description_length
    config.include_links = include_links
    return config


class TestResolveDetail:
    def test_explicit_summary(self) -> None:
        assert _resolve_detail("summary", None) == "summary"

    def test_explicit_full(self) -> None:
        assert _resolve_detail("full", None) == "full"

    def test_invalid_detail(self) -> None:
        with pytest.raises(ValueError, match="Invalid detail level"):
            _resolve_detail("brief", None)

    def test_none_with_no_config(self) -> None:
        assert _resolve_detail(None, None) == "full"

    def test_none_with_config(self) -> None:
        config = _make_config(default_detail="summary")
        assert _resolve_detail(None, config) == "summary"


class TestMaxDesc:
    def test_with_config(self) -> None:
        config = _make_config(max_description_length=200)
        assert _max_desc(config) == 200

    def test_without_config(self) -> None:
        assert _max_desc(None) == 500


class TestLinks:
    def test_with_config_true(self) -> None:
        assert _links(_make_config(include_links=True)) is True

    def test_with_config_false(self) -> None:
        assert _links(_make_config(include_links=False)) is False

    def test_without_config(self) -> None:
        assert _links(None) is False


class TestTruncateText:
    def test_none_input(self) -> None:
        assert truncate_text(None, 100) is None

    def test_short_text(self) -> None:
        assert truncate_text("hello", 100) == "hello"

    def test_exact_length(self) -> None:
        assert truncate_text("hello", 5) == "hello"

    def test_truncated(self) -> None:
        assert truncate_text("hello world", 5) == "hello..."

    def test_zero_no_limit(self) -> None:
        long = "x" * 10000
        assert truncate_text(long, 0) == long


class TestExtractName:
    def test_none(self) -> None:
        assert _extract_name(None) is None

    def test_dict_display_name(self) -> None:
        assert _extract_name({"displayName": "Alice"}) == "Alice"

    def test_dict_name(self) -> None:
        assert _extract_name({"name": "dev"}) == "dev"

    def test_dict_title(self) -> None:
        assert _extract_name({"title": "My Page"}) == "My Page"

    def test_string(self) -> None:
        assert _extract_name("raw") == "raw"


class TestExtractBodyText:
    def test_with_body(self) -> None:
        raw = {"body": {"storage": {"value": "<p>Hello</p>"}}}
        assert _extract_body_text(raw) == "<p>Hello</p>"

    def test_no_body(self) -> None:
        assert _extract_body_text({}) is None

    def test_empty_body(self) -> None:
        assert _extract_body_text({"body": {}}) is None


class TestFormatPage:
    def test_basic(self) -> None:
        raw = {
            "id": "123",
            "title": "My Page",
            "type": "page",
            "status": "current",
            "space": {"key": "DEV", "name": "Development"},
            "version": {"number": 5},
            "body": {"storage": {"value": "<p>Content here</p>"}},
        }
        result = format_page(raw, _make_config())
        assert result["id"] == "123"
        assert result["title"] == "My Page"
        assert result["type"] == "page"
        assert result["status"] == "current"
        assert result["space"] == "Development"
        assert result["version"] == 5
        assert result["body"] == "<p>Content here</p>"
        assert "self" not in result

    def test_with_links(self) -> None:
        raw = {
            "id": "123",
            "title": "P",
            "type": "page",
            "status": "current",
            "_links": {"self": "/rest/api/content/123", "webui": "/display/DEV/P"},
        }
        result = format_page(raw, _make_config(include_links=True))
        assert result["self"] == "/rest/api/content/123"
        assert result["webui"] == "/display/DEV/P"

    def test_no_version(self) -> None:
        raw = {"id": "1", "title": "T"}
        result = format_page(raw, None)
        assert "version" not in result

    def test_no_body(self) -> None:
        raw = {"id": "1", "title": "T"}
        result = format_page(raw, None)
        assert "body" not in result

    def test_body_truncated(self) -> None:
        raw = {"id": "1", "title": "T", "body": {"storage": {"value": "x" * 600}}}
        result = format_page(raw, _make_config(max_description_length=100))
        assert len(result["body"]) == 103  # 100 + "..."


class TestFormatPages:
    def test_basic(self) -> None:
        raw = {
            "results": [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}],
            "size": 2,
            "start": 0,
            "limit": 25,
        }
        result = format_pages(raw, _make_config())
        assert result["size"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "1"

    def test_empty(self) -> None:
        result = format_pages({"results": []}, None)
        assert result["size"] == 0
        assert result["results"] == []


class TestFormatSpace:
    def test_basic(self) -> None:
        raw = {
            "key": "DEV",
            "name": "Development",
            "type": "global",
            "description": {"plain": {"value": "Dev space"}},
        }
        result = format_space(raw, _make_config())
        assert result["key"] == "DEV"
        assert result["name"] == "Development"
        assert result["description"] == "Dev space"

    def test_string_description(self) -> None:
        raw = {"key": "K", "name": "N", "description": "plain text"}
        result = format_space(raw, _make_config())
        assert result["description"] == "plain text"

    def test_no_description(self) -> None:
        raw = {"key": "K", "name": "N"}
        result = format_space(raw, None)
        assert "description" not in result

    def test_with_links(self) -> None:
        raw = {"key": "K", "name": "N", "_links": {"self": "/rest/api/space/K"}}
        result = format_space(raw, _make_config(include_links=True))
        assert result["self"] == "/rest/api/space/K"


class TestFormatSpaces:
    def test_basic(self) -> None:
        raw = {"results": [{"key": "A"}, {"key": "B"}], "size": 2, "start": 0, "limit": 25}
        result = format_spaces(raw, _make_config())
        assert result["size"] == 2
        assert len(result["results"]) == 2


class TestFormatComment:
    def test_basic(self) -> None:
        raw = {
            "id": "456",
            "author": {"displayName": "Alice"},
            "created": "2024-01-01",
            "body": {"storage": {"value": "<p>A comment</p>"}},
        }
        result = format_comment(raw, _make_config())
        assert result["id"] == "456"
        assert result["author"] == "Alice"
        assert result["body"] == "<p>A comment</p>"

    def test_no_body(self) -> None:
        raw = {"id": "1", "author": {"displayName": "Bob"}}
        result = format_comment(raw, None)
        assert "body" not in result

    def test_history_style(self) -> None:
        raw = {"id": "1", "by": {"displayName": "Carol"}, "when": "2024-06-01"}
        result = format_comment(raw, None)
        assert result["author"] == "Carol"
        assert result["created"] == "2024-06-01"

    def test_with_links(self) -> None:
        raw = {"id": "1", "_links": {"self": "/comment/1"}}
        result = format_comment(raw, _make_config(include_links=True))
        assert result["self"] == "/comment/1"


class TestFormatComments:
    def test_basic(self) -> None:
        raw = {
            "results": [{"id": "1"}, {"id": "2"}],
            "size": 2,
            "start": 0,
            "limit": 25,
        }
        result = format_comments(raw, _make_config())
        assert result["size"] == 2
        assert len(result["results"]) == 2


class TestFormatAttachment:
    def test_basic(self) -> None:
        raw = {
            "id": "att1",
            "title": "image.png",
            "extensions": {"mediaType": "image/png", "fileSize": 1024},
        }
        result = format_attachment(raw, _make_config())
        assert result["id"] == "att1"
        assert result["title"] == "image.png"
        assert result["mediaType"] == "image/png"
        assert result["fileSize"] == 1024
        assert "self" not in result

    def test_with_links(self) -> None:
        raw = {
            "id": "att1",
            "title": "f.txt",
            "extensions": {},
            "_links": {"self": "/api/att1", "download": "/download/att1"},
        }
        result = format_attachment(raw, _make_config(include_links=True))
        assert result["self"] == "/api/att1"
        assert result["download"] == "/download/att1"

    def test_no_extensions(self) -> None:
        raw = {"id": "att1", "title": "f.txt"}
        result = format_attachment(raw, None)
        assert result["mediaType"] is None
        assert result["fileSize"] is None


class TestFormatAttachments:
    def test_basic(self) -> None:
        raw = {"results": [{"id": "att1"}], "size": 1, "start": 0, "limit": 25}
        result = format_attachments(raw, _make_config())
        assert result["size"] == 1


class TestFormatUser:
    def test_cloud_user(self) -> None:
        raw = {
            "accountId": "abc123",
            "displayName": "Alice",
            "email": "alice@example.com",
            "type": "known",
        }
        result = format_user(raw, _make_config())
        assert result["accountId"] == "abc123"
        assert result["displayName"] == "Alice"
        assert result["email"] == "alice@example.com"

    def test_dc_user(self) -> None:
        raw = {"userKey": "bob", "displayName": "Bob"}
        result = format_user(raw, None)
        assert result["accountId"] == "bob"

    def test_with_links(self) -> None:
        raw = {"accountId": "x", "_links": {"self": "/user/x"}}
        result = format_user(raw, _make_config(include_links=True))
        assert result["self"] == "/user/x"


class TestFormatSearchResult:
    def test_basic(self) -> None:
        raw = {
            "content": {
                "id": "123",
                "title": "Found Page",
                "type": "page",
                "status": "current",
                "space": {"name": "Dev"},
            },
            "excerpt": "...matching text...",
        }
        result = format_search_result(raw, _make_config())
        assert result["id"] == "123"
        assert result["title"] == "Found Page"
        assert result["space"] == "Dev"
        assert result["excerpt"] == "...matching text..."
        assert "url" not in result

    def test_with_links(self) -> None:
        raw = {"content": {"id": "1"}, "url": "/wiki/page/1"}
        result = format_search_result(raw, _make_config(include_links=True))
        assert result["url"] == "/wiki/page/1"

    def test_fallback_title(self) -> None:
        raw = {"content": {}, "title": "Fallback"}
        result = format_search_result(raw, None)
        assert result["title"] == "Fallback"


class TestFormatSearchResults:
    def test_basic(self) -> None:
        raw = {
            "results": [{"content": {"id": "1"}}],
            "totalSize": 50,
            "size": 1,
            "start": 0,
            "limit": 25,
        }
        result = format_search_results(raw, _make_config())
        assert result["totalSize"] == 50
        assert result["size"] == 1


class TestFormatLabel:
    def test_basic(self) -> None:
        raw = {"name": "important", "prefix": "global", "id": "1"}
        result = format_label(raw)
        assert result["name"] == "important"
        assert result["prefix"] == "global"


class TestFormatLabels:
    def test_basic(self) -> None:
        raw = {"results": [{"name": "a"}, {"name": "b"}], "size": 2}
        result = format_labels(raw)
        assert result["size"] == 2
        assert len(result["results"]) == 2

    def test_empty(self) -> None:
        result = format_labels({"results": []})
        assert result["size"] == 0
