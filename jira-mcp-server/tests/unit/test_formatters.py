"""Tests for response formatters."""

from unittest.mock import MagicMock

import pytest

from jira_mcp_server.formatters import (
    _extract_name,
    _extract_names,
    _get_summary_api_fields,
    _resolve_detail,
    format_board,
    format_comment,
    format_comments,
    format_issue,
    format_issues,
    format_project,
    format_projects,
    format_sprint,
    format_user,
    format_users,
    truncate_text,
)


def _make_config(
    default_detail: str = "summary",
    max_description_length: int = 500,
    include_links: bool = False,
    summary_fields: str | None = None,
) -> MagicMock:
    config = MagicMock()
    config.default_detail = default_detail
    config.max_description_length = max_description_length
    config.include_links = include_links
    config.summary_fields = summary_fields
    return config


class TestResolveDetail:
    def test_explicit_summary(self) -> None:
        assert _resolve_detail("summary", _make_config()) == "summary"

    def test_explicit_full(self) -> None:
        assert _resolve_detail("full", _make_config()) == "full"

    def test_invalid_detail_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid detail level"):
            _resolve_detail("verbose", _make_config())

    def test_none_uses_config_default(self) -> None:
        assert _resolve_detail(None, _make_config(default_detail="full")) == "full"
        assert _resolve_detail(None, _make_config(default_detail="summary")) == "summary"

    def test_none_config_defaults_to_full(self) -> None:
        assert _resolve_detail(None, None) == "full"

    def test_explicit_overrides_config(self) -> None:
        assert _resolve_detail("full", _make_config(default_detail="summary")) == "full"


class TestGetSummaryApiFields:
    def test_default_fields(self) -> None:
        result = _get_summary_api_fields(_make_config())
        assert "summary" in result
        assert "status" in result
        assert "assignee" in result

    def test_custom_fields_override(self) -> None:
        config = _make_config(summary_fields="key,summary,status")
        assert _get_summary_api_fields(config) == "key,summary,status"

    def test_none_config_returns_defaults(self) -> None:
        result = _get_summary_api_fields(None)
        assert "summary" in result


class TestTruncateText:
    def test_none_returns_none(self) -> None:
        assert truncate_text(None, 100) is None

    def test_short_text_unchanged(self) -> None:
        assert truncate_text("hello", 100) == "hello"

    def test_long_text_truncated(self) -> None:
        result = truncate_text("a" * 600, 500)
        assert len(result) == 503
        assert result.endswith("...")

    def test_exact_length_not_truncated(self) -> None:
        assert truncate_text("a" * 500, 500) == "a" * 500

    def test_zero_max_means_no_limit(self) -> None:
        text = "a" * 10000
        assert truncate_text(text, 0) == text


class TestExtractName:
    def test_none(self) -> None:
        assert _extract_name(None) is None

    def test_dict_display_name(self) -> None:
        assert _extract_name({"displayName": "Troy"}) == "Troy"

    def test_dict_name(self) -> None:
        assert _extract_name({"name": "troy"}) == "troy"

    def test_dict_value(self) -> None:
        assert _extract_name({"value": "High"}) == "High"

    def test_dict_priority(self) -> None:
        assert _extract_name({"displayName": "Troy", "name": "troy"}) == "Troy"

    def test_string_passthrough(self) -> None:
        assert _extract_name("direct") == "direct"


class TestExtractNames:
    def test_none(self) -> None:
        assert _extract_names(None) == []

    def test_empty_list(self) -> None:
        assert _extract_names([]) == []

    def test_list_of_dicts(self) -> None:
        items = [{"name": "backend"}, {"name": "frontend"}]
        assert _extract_names(items) == ["backend", "frontend"]

    def test_filters_none_values(self) -> None:
        items = [{"name": "a"}, {}, {"name": "b"}]
        assert _extract_names(items) == ["a", "b"]

    def test_non_list(self) -> None:
        assert _extract_names("not a list") == []


class TestFormatIssue:
    def test_basic_format(self) -> None:
        raw = {
            "key": "PROJ-1",
            "self": "https://jira/issue/1",
            "fields": {
                "summary": "Fix bug",
                "description": "Something is broken",
                "status": {"name": "Open"},
                "assignee": {"displayName": "Troy"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Bug"},
                "labels": ["backend"],
                "components": [{"name": "auth"}],
                "resolution": None,
                "created": "2024-01-01",
                "updated": "2024-01-02",
                "duedate": "2024-02-01",
            },
        }
        config = _make_config()
        result = format_issue(raw, config)
        assert result["key"] == "PROJ-1"
        assert result["summary"] == "Fix bug"
        assert result["status"] == "Open"
        assert result["assignee"] == "Troy"
        assert result["priority"] == "High"
        assert result["type"] == "Bug"
        assert result["labels"] == ["backend"]
        assert result["components"] == ["auth"]
        assert result["resolution"] is None
        assert result["created"] == "2024-01-01"
        assert result["duedate"] == "2024-02-01"
        assert "self" not in result

    def test_include_links(self) -> None:
        raw = {"key": "PROJ-1", "self": "https://jira/issue/1", "fields": {}}
        config = _make_config(include_links=True)
        result = format_issue(raw, config)
        assert result["self"] == "https://jira/issue/1"

    def test_truncates_description(self) -> None:
        raw = {"key": "PROJ-1", "fields": {"description": "x" * 600}}
        config = _make_config(max_description_length=100)
        result = format_issue(raw, config)
        assert len(result["description"]) == 103
        assert result["description"].endswith("...")


class TestFormatIssues:
    def test_formats_search_result(self) -> None:
        raw = {
            "total": 2,
            "startAt": 0,
            "maxResults": 50,
            "issues": [
                {"key": "PROJ-1", "fields": {"summary": "A"}},
                {"key": "PROJ-2", "fields": {"summary": "B"}},
            ],
        }
        config = _make_config()
        result = format_issues(raw, config)
        assert result["total"] == 2
        assert result["startAt"] == 0
        assert len(result["issues"]) == 2
        assert result["issues"][0]["key"] == "PROJ-1"

    def test_empty_issues(self) -> None:
        raw = {"total": 0, "startAt": 0, "maxResults": 50, "issues": []}
        result = format_issues(raw, _make_config())
        assert result["issues"] == []


class TestFormatProject:
    def test_basic(self) -> None:
        raw = {
            "key": "PROJ",
            "name": "Project",
            "description": "A project",
            "lead": {"displayName": "Troy"},
            "projectTypeKey": "software",
            "self": "https://jira/project/1",
        }
        config = _make_config()
        result = format_project(raw, config)
        assert result["key"] == "PROJ"
        assert result["name"] == "Project"
        assert result["lead"] == "Troy"
        assert "self" not in result

    def test_include_links(self) -> None:
        raw = {"key": "PROJ", "self": "https://jira/project/1"}
        config = _make_config(include_links=True)
        result = format_project(raw, config)
        assert result["self"] == "https://jira/project/1"


class TestFormatProjects:
    def test_formats_list(self) -> None:
        raw = [{"key": "A", "name": "Alpha"}, {"key": "B", "name": "Beta"}]
        result = format_projects(raw, _make_config())
        assert len(result) == 2
        assert result[0]["key"] == "A"


class TestFormatComment:
    def test_basic(self) -> None:
        raw = {
            "id": "123",
            "author": {"displayName": "Troy"},
            "body": "Great work!",
            "created": "2024-01-01",
            "updated": "2024-01-02",
            "self": "https://jira/comment/123",
        }
        config = _make_config()
        result = format_comment(raw, config)
        assert result["id"] == "123"
        assert result["author"] == "Troy"
        assert result["body"] == "Great work!"
        assert "self" not in result

    def test_include_links(self) -> None:
        raw = {"id": "1", "self": "https://jira/comment/1"}
        config = _make_config(include_links=True)
        assert format_comment(raw, config)["self"] == "https://jira/comment/1"


class TestFormatComments:
    def test_formats_list(self) -> None:
        raw = {
            "total": 1,
            "comments": [{"id": "1", "body": "test", "author": {"name": "troy"}}],
        }
        result = format_comments(raw, _make_config())
        assert result["total"] == 1
        assert len(result["comments"]) == 1

    def test_empty(self) -> None:
        raw = {"comments": []}
        result = format_comments(raw, _make_config())
        assert result["total"] == 0


class TestFormatUser:
    def test_basic(self) -> None:
        raw = {
            "key": "troy",
            "name": "troy",
            "displayName": "Troy",
            "emailAddress": "troy@example.com",
            "active": True,
            "self": "https://jira/user/troy",
        }
        config = _make_config()
        result = format_user(raw, config)
        assert result["displayName"] == "Troy"
        assert result["emailAddress"] == "troy@example.com"
        assert "self" not in result

    def test_include_links(self) -> None:
        raw = {"name": "troy", "self": "https://jira/user/troy"}
        config = _make_config(include_links=True)
        assert format_user(raw, config)["self"] == "https://jira/user/troy"


class TestFormatUsers:
    def test_formats_list(self) -> None:
        raw = [{"name": "a"}, {"name": "b"}]
        result = format_users(raw, _make_config())
        assert len(result) == 2


class TestFormatSprint:
    def test_basic(self) -> None:
        raw = {
            "id": 42,
            "name": "Sprint 1",
            "state": "active",
            "startDate": "2024-01-01",
            "endDate": "2024-01-14",
            "completeDate": None,
            "goal": "Ship feature X",
            "self": "https://jira/sprint/42",
        }
        config = _make_config()
        result = format_sprint(raw, config)
        assert result["id"] == 42
        assert result["name"] == "Sprint 1"
        assert result["state"] == "active"
        assert result["goal"] == "Ship feature X"
        assert "self" not in result

    def test_include_links(self) -> None:
        raw = {"id": 1, "self": "https://jira/sprint/1"}
        config = _make_config(include_links=True)
        assert format_sprint(raw, config)["self"] == "https://jira/sprint/1"


class TestFormatBoard:
    def test_basic(self) -> None:
        raw = {
            "id": 10,
            "name": "My Board",
            "type": "scrum",
            "location": {"projectKey": "PROJ", "projectName": "Project"},
            "self": "https://jira/board/10",
        }
        config = _make_config()
        result = format_board(raw, config)
        assert result["id"] == 10
        assert result["name"] == "My Board"
        assert result["type"] == "scrum"
        assert result["projectKey"] == "PROJ"
        assert "self" not in result

    def test_no_location(self) -> None:
        raw = {"id": 10, "name": "Board", "type": "kanban"}
        result = format_board(raw, _make_config())
        assert "projectKey" not in result

    def test_include_links(self) -> None:
        raw = {"id": 1, "self": "https://jira/board/1"}
        config = _make_config(include_links=True)
        assert format_board(raw, config)["self"] == "https://jira/board/1"
