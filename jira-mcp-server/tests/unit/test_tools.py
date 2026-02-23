"""Tests for all tool modules."""

from unittest.mock import MagicMock, patch

import pytest

from jira_mcp_server.models import FieldSchema, FieldType

# --- Helpers ---


def _mock_client() -> MagicMock:
    return MagicMock()


def _make_field_schema(key: str = "summary", required: bool = False) -> FieldSchema:
    return FieldSchema(key=key, name="Summary", type=FieldType.STRING, required=required, custom=False)


# ===================== issue_tools =====================


class TestIssueToolsInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import issue_tools

        config = MagicMock()
        config.cache_ttl = 3600
        issue_tools.initialize_issue_tools(config)
        assert issue_tools._client is not None
        assert issue_tools._cache is not None
        assert issue_tools._validator is not None


class TestGetFieldSchema:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._cache = None
        issue_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            issue_tools._get_field_schema("PROJ", "Task")

    def test_returns_cached(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_cache = MagicMock()
        mock_cache.get.return_value = [_make_field_schema()]
        issue_tools._cache = mock_cache
        issue_tools._client = _mock_client()
        result = issue_tools._get_field_schema("PROJ", "Task")
        assert len(result) == 1
        mock_cache.get.assert_called_once_with("PROJ", "Task")

    def test_fetches_and_caches(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_client = _mock_client()
        mock_client.get_project_schema.return_value = [
            {
                "key": "summary",
                "name": "Summary",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
        issue_tools._cache = mock_cache
        issue_tools._client = mock_client
        result = issue_tools._get_field_schema("PROJ", "Task")
        assert len(result) == 1
        assert result[0].key == "summary"
        mock_cache.set.assert_called_once()

    def test_schema_type_mapping(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_client = _mock_client()
        mock_client.get_project_schema.return_value = [
            {"key": "f1", "name": "Num", "required": False, "schema": {"type": "number"}},
            {"key": "f2", "name": "Dt", "required": False, "schema": {"type": "date"}},
            {"key": "f3", "name": "Dtt", "required": False, "schema": {"type": "datetime"}},
            {"key": "f4", "name": "Usr", "required": False, "schema": {"type": "user"}},
            {"key": "f5", "name": "Opt", "required": False, "schema": {"type": "option"}},
            {"key": "f6", "name": "Arr", "required": False, "schema": {"type": "array"}},
            {"key": "f7", "name": "Str", "required": False, "schema": {"type": "unknowntype"}},
        ]
        issue_tools._cache = mock_cache
        issue_tools._client = mock_client
        result = issue_tools._get_field_schema("PROJ", "Task")
        assert result[0].type == FieldType.NUMBER
        assert result[1].type == FieldType.DATE
        assert result[2].type == FieldType.DATETIME
        assert result[3].type == FieldType.USER
        assert result[4].type == FieldType.OPTION
        assert result[5].type == FieldType.ARRAY
        assert result[6].type == FieldType.STRING

    def test_allowed_values_with_value_key(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_client = _mock_client()
        mock_client.get_project_schema.return_value = [
            {
                "key": "priority",
                "name": "Priority",
                "required": False,
                "schema": {"type": "option"},
                "allowedValues": [{"value": "High"}, {"value": "Low"}],
            }
        ]
        issue_tools._cache = mock_cache
        issue_tools._client = mock_client
        result = issue_tools._get_field_schema("PROJ", "Task")
        assert result[0].allowed_values == ["High", "Low"]

    def test_allowed_values_with_name_key(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_client = _mock_client()
        mock_client.get_project_schema.return_value = [
            {
                "key": "issuetype",
                "name": "Issue Type",
                "required": True,
                "schema": {"type": "option"},
                "allowedValues": [{"name": "Task"}, {"name": "Bug"}],
            }
        ]
        issue_tools._cache = mock_cache
        issue_tools._client = mock_client
        result = issue_tools._get_field_schema("PROJ", "Task")
        assert result[0].allowed_values == ["Task", "Bug"]

    def test_custom_field_detection(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_client = _mock_client()
        mock_client.get_project_schema.return_value = [
            {"key": "customfield_10001", "name": "Custom", "required": False, "schema": {"type": "string"}},
            {"key": "summary", "name": "Summary", "required": True, "schema": {"type": "string"}, "custom": True},
        ]
        issue_tools._cache = mock_cache
        issue_tools._client = mock_client
        result = issue_tools._get_field_schema("PROJ", "Task")
        assert result[0].custom is True
        assert result[1].custom is True


class TestIssueCreate:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = None
        issue_tools._validator = None
        with pytest.raises(RuntimeError, match="not initialized"):
            issue_tools.jira_issue_create(project="PROJ", summary="Test")

    def test_success(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.create_issue.return_value = {"key": "PROJ-1"}
        issue_tools._client = mock_client
        issue_tools._validator = MagicMock()
        with patch.object(issue_tools, "_get_field_schema", return_value=[]):
            result = issue_tools.jira_issue_create(project="PROJ", summary="Test")
        assert result["key"] == "PROJ-1"

    def test_with_all_fields(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.create_issue.return_value = {"key": "PROJ-1"}
        issue_tools._client = mock_client
        issue_tools._validator = MagicMock()
        with patch.object(issue_tools, "_get_field_schema", return_value=[]):
            result = issue_tools.jira_issue_create(
                project="PROJ",
                summary="Test",
                issue_type="Bug",
                description="desc",
                priority="High",
                assignee="john",
                labels=["bug"],
                due_date="2024-12-31",
                customfield_10001="custom_val",
            )
        assert result["key"] == "PROJ-1"

    def test_description_markdown_converted(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.create_issue.return_value = {"key": "PROJ-1"}
        issue_tools._client = mock_client
        issue_tools._cache = MagicMock()
        issue_tools._cache.get.return_value = []
        issue_tools._validator = MagicMock()
        issue_tools.jira_issue_create(
            project="PROJ",
            summary="Test",
            description="**bold** and [link](http://example.com)",
        )
        call_data = mock_client.create_issue.call_args[0][0]
        assert call_data["fields"]["description"] == "*bold* and [link|http://example.com]"

    def test_schema_fetch_failure(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        issue_tools._validator = MagicMock()
        with patch.object(issue_tools, "_get_field_schema", side_effect=ValueError("schema error")):
            with pytest.raises(ValueError, match="Failed to get project schema"):
                issue_tools.jira_issue_create(project="PROJ", summary="Test")

    def test_validation_failure(self) -> None:
        from jira_mcp_server.models import FieldValidationError
        from jira_mcp_server.tools import issue_tools

        mock_validator = MagicMock()
        mock_validator.validate_fields.side_effect = FieldValidationError("field", "bad")
        issue_tools._client = _mock_client()
        issue_tools._validator = mock_validator
        with patch.object(issue_tools, "_get_field_schema", return_value=[]):
            with pytest.raises(ValueError, match="Validation failed"):
                issue_tools.jira_issue_create(project="PROJ", summary="Test")

    def test_client_create_failure(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.create_issue.side_effect = ValueError("API error")
        issue_tools._client = mock_client
        issue_tools._validator = MagicMock()
        with patch.object(issue_tools, "_get_field_schema", return_value=[]):
            with pytest.raises(ValueError, match="Failed to create issue"):
                issue_tools.jira_issue_create(project="PROJ", summary="Test")


class TestIssueUpdate:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            issue_tools.jira_issue_update(issue_key="TEST-1", summary="Updated")

    def test_success(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.get_issue.return_value = {"key": "TEST-1", "fields": {"summary": "Updated"}}
        issue_tools._client = mock_client
        result = issue_tools.jira_issue_update(issue_key="TEST-1", summary="Updated")
        assert result["key"] == "TEST-1"
        mock_client.update_issue.assert_called_once()

    def test_with_all_fields(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.get_issue.return_value = {"key": "TEST-1"}
        issue_tools._client = mock_client
        issue_tools.jira_issue_update(
            issue_key="TEST-1",
            summary="s",
            description="d",
            priority="High",
            assignee="john",
            labels=["l"],
            due_date="2024-12-31",
            customfield_10001="v",
        )
        call_data = mock_client.update_issue.call_args[0][1]
        assert call_data["fields"]["summary"] == "s"
        assert call_data["fields"]["description"] == "d"
        assert call_data["fields"]["priority"] == {"name": "High"}
        assert call_data["fields"]["assignee"] == {"name": "john"}
        assert call_data["fields"]["labels"] == ["l"]
        assert call_data["fields"]["duedate"] == "2024-12-31"
        assert call_data["fields"]["customfield_10001"] == "v"

    def test_description_markdown_converted(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.get_issue.return_value = {"key": "TEST-1"}
        issue_tools._client = mock_client
        issue_tools.jira_issue_update(issue_key="TEST-1", description="# Heading\n\n**bold**")
        call_data = mock_client.update_issue.call_args[0][1]
        assert call_data["fields"]["description"] == "h1. Heading\n\n*bold*"

    def test_no_fields_raises(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        with pytest.raises(ValueError, match="No fields provided"):
            issue_tools.jira_issue_update(issue_key="TEST-1")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.update_issue.side_effect = ValueError("API error")
        issue_tools._client = mock_client
        with pytest.raises(ValueError, match="Failed to update issue"):
            issue_tools.jira_issue_update(issue_key="TEST-1", summary="Updated")


class TestIssueGet:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            issue_tools.jira_issue_get("TEST-1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.get_issue.return_value = {"key": "TEST-1"}
        issue_tools._client = mock_client
        result = issue_tools.jira_issue_get("TEST-1")
        assert result["key"] == "TEST-1"

    def test_failure(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.get_issue.side_effect = ValueError("not found")
        issue_tools._client = mock_client
        with pytest.raises(ValueError, match="Failed to get issue"):
            issue_tools.jira_issue_get("TEST-1")


class TestIssueDelete:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            issue_tools.jira_issue_delete("TEST-1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        result = issue_tools.jira_issue_delete("TEST-1")
        assert result["success"] is True

    def test_with_subtasks(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        issue_tools._client = mock_client
        issue_tools.jira_issue_delete("TEST-1", delete_subtasks=True)
        mock_client.delete_issue.assert_called_once_with("TEST-1", delete_subtasks=True)

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            issue_tools.jira_issue_delete("")

    def test_whitespace_key_raises(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            issue_tools.jira_issue_delete("  ")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.delete_issue.side_effect = ValueError("error")
        issue_tools._client = mock_client
        with pytest.raises(ValueError, match="Failed to delete issue"):
            issue_tools.jira_issue_delete("TEST-1")


class TestIssueLink:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            issue_tools.jira_issue_link("Blocks", "TEST-1", "TEST-2")

    def test_success(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        result = issue_tools.jira_issue_link("Blocks", "TEST-1", "TEST-2")
        assert result["success"] is True

    def test_empty_link_type(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Link type cannot be empty"):
            issue_tools.jira_issue_link("", "TEST-1", "TEST-2")

    def test_whitespace_link_type(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Link type cannot be empty"):
            issue_tools.jira_issue_link("  ", "TEST-1", "TEST-2")

    def test_empty_inward_issue(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Inward issue key cannot be empty"):
            issue_tools.jira_issue_link("Blocks", "", "TEST-2")

    def test_empty_outward_issue(self) -> None:
        from jira_mcp_server.tools import issue_tools

        issue_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Outward issue key cannot be empty"):
            issue_tools.jira_issue_link("Blocks", "TEST-1", "")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.link_issues.side_effect = ValueError("error")
        issue_tools._client = mock_client
        with pytest.raises(ValueError, match="Failed to link issues"):
            issue_tools.jira_issue_link("Blocks", "TEST-1", "TEST-2")


# ===================== search_tools =====================


class TestBuildJql:
    def test_empty_criteria(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        assert build_jql_from_criteria() == ""

    def test_project_only(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        assert build_jql_from_criteria(project="TEST") == 'project = "TEST"'

    def test_assignee(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        assert build_jql_from_criteria(assignee="john") == 'assignee = "john"'

    def test_assignee_current_user(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        assert build_jql_from_criteria(assignee="currentUser()") == "assignee = currentUser()"

    def test_status(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        jql = build_jql_from_criteria(status="In Progress")
        assert 'status = "In Progress"' in jql

    def test_priority(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        jql = build_jql_from_criteria(priority="High")
        assert 'priority = "High"' in jql

    def test_labels(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        jql = build_jql_from_criteria(labels=["bug", "urgent"])
        assert 'labels = "bug"' in jql
        assert 'labels = "urgent"' in jql

    def test_created_dates(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        jql = build_jql_from_criteria(created_after="2024-01-01", created_before="2024-12-31")
        assert 'created >= "2024-01-01"' in jql
        assert 'created <= "2024-12-31"' in jql

    def test_updated_dates(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        jql = build_jql_from_criteria(updated_after="2024-01-01", updated_before="2024-12-31")
        assert 'updated >= "2024-01-01"' in jql
        assert 'updated <= "2024-12-31"' in jql

    def test_multiple_criteria(self) -> None:
        from jira_mcp_server.tools.search_tools import build_jql_from_criteria

        jql = build_jql_from_criteria(project="TEST", assignee="john", status="Open")
        assert " AND " in jql


class TestSearchIssues:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import search_tools

        search_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            search_tools.jira_search_issues(project="TEST")

    def test_success(self) -> None:
        from jira_mcp_server.tools import search_tools

        mock_client = _mock_client()
        mock_client.search_issues.return_value = {"issues": [], "total": 0}
        search_tools._client = mock_client
        result = search_tools.jira_search_issues(project="TEST")
        assert result["total"] == 0

    def test_no_criteria_raises(self) -> None:
        from jira_mcp_server.tools import search_tools

        search_tools._client = _mock_client()
        with pytest.raises(ValueError, match="At least one search criterion"):
            search_tools.jira_search_issues()

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import search_tools

        mock_client = _mock_client()
        mock_client.search_issues.side_effect = ValueError("bad jql")
        search_tools._client = mock_client
        with pytest.raises(ValueError, match="Search failed"):
            search_tools.jira_search_issues(project="TEST")


class TestSearchJql:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import search_tools

        search_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            search_tools.jira_search_jql("project = TEST")

    def test_success(self) -> None:
        from jira_mcp_server.tools import search_tools

        mock_client = _mock_client()
        mock_client.search_issues.return_value = {"issues": [], "total": 0}
        search_tools._client = mock_client
        result = search_tools.jira_search_jql("project = TEST")
        assert result["total"] == 0

    def test_empty_jql_raises(self) -> None:
        from jira_mcp_server.tools import search_tools

        search_tools._client = _mock_client()
        with pytest.raises(ValueError, match="JQL query cannot be empty"):
            search_tools.jira_search_jql("")

    def test_whitespace_jql_raises(self) -> None:
        from jira_mcp_server.tools import search_tools

        search_tools._client = _mock_client()
        with pytest.raises(ValueError, match="JQL query cannot be empty"):
            search_tools.jira_search_jql("  ")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import search_tools

        mock_client = _mock_client()
        mock_client.search_issues.side_effect = ValueError("error")
        search_tools._client = mock_client
        with pytest.raises(ValueError, match="JQL search failed"):
            search_tools.jira_search_jql("bad query")


class TestSearchInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import search_tools

        mock_client = _mock_client()
        mock_config = MagicMock()
        search_tools.initialize_search_tools(mock_client, mock_config)
        assert search_tools._client is mock_client
        assert search_tools._config is mock_config


# ===================== filter_tools =====================


class TestFilterCreate:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            filter_tools.jira_filter_create("name", "jql")

    def test_success(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.create_filter.return_value = {"id": "100"}
        filter_tools._client = mock_client
        result = filter_tools.jira_filter_create("My Filter", "project = TEST")
        assert result["id"] == "100"

    def test_empty_name_raises(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Filter name cannot be empty"):
            filter_tools.jira_filter_create("", "project = TEST")

    def test_whitespace_name_raises(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Filter name cannot be empty"):
            filter_tools.jira_filter_create("  ", "project = TEST")

    def test_empty_jql_raises(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        with pytest.raises(ValueError, match="JQL query cannot be empty"):
            filter_tools.jira_filter_create("name", "")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.create_filter.side_effect = ValueError("error")
        filter_tools._client = mock_client
        with pytest.raises(ValueError, match="Filter creation failed"):
            filter_tools.jira_filter_create("name", "jql")


class TestFilterList:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            filter_tools.jira_filter_list()

    def test_success(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.list_filters.return_value = [{"id": "100"}]
        filter_tools._client = mock_client
        result = filter_tools.jira_filter_list()
        assert len(result) == 1

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.list_filters.side_effect = ValueError("error")
        filter_tools._client = mock_client
        with pytest.raises(ValueError, match="Filter list failed"):
            filter_tools.jira_filter_list()


class TestFilterGet:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            filter_tools.jira_filter_get("100")

    def test_success(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.get_filter.return_value = {"id": "100", "jql": "proj = X"}
        filter_tools._client = mock_client
        result = filter_tools.jira_filter_get("100")
        assert result["id"] == "100"

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Filter ID cannot be empty"):
            filter_tools.jira_filter_get("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.get_filter.side_effect = ValueError("error")
        filter_tools._client = mock_client
        with pytest.raises(ValueError, match="Get filter failed"):
            filter_tools.jira_filter_get("100")


class TestFilterExecute:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            filter_tools.jira_filter_execute("100")

    def test_success(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.get_filter.return_value = {"id": "100", "jql": "project = TEST"}
        mock_client.search_issues.return_value = {"issues": [], "total": 0}
        filter_tools._client = mock_client
        result = filter_tools.jira_filter_execute("100")
        assert result["total"] == 0

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Filter ID cannot be empty"):
            filter_tools.jira_filter_execute("")

    def test_no_jql_in_filter(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.get_filter.return_value = {"id": "100"}
        filter_tools._client = mock_client
        with pytest.raises(ValueError, match="Filter execution failed"):
            filter_tools.jira_filter_execute("100")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.get_filter.side_effect = ValueError("error")
        filter_tools._client = mock_client
        with pytest.raises(ValueError, match="Filter execution failed"):
            filter_tools.jira_filter_execute("100")


class TestFilterUpdate:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            filter_tools.jira_filter_update("100", name="New")

    def test_success(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.update_filter.return_value = {"id": "100", "name": "Updated"}
        filter_tools._client = mock_client
        result = filter_tools.jira_filter_update("100", name="Updated")
        assert result["name"] == "Updated"

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Filter ID cannot be empty"):
            filter_tools.jira_filter_update("", name="x")

    def test_no_fields_raises(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        with pytest.raises(ValueError, match="At least one field"):
            filter_tools.jira_filter_update("100")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.update_filter.side_effect = ValueError("error")
        filter_tools._client = mock_client
        with pytest.raises(ValueError, match="Filter update failed"):
            filter_tools.jira_filter_update("100", name="x")


class TestFilterDelete:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            filter_tools.jira_filter_delete("100")

    def test_success(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        result = filter_tools.jira_filter_delete("100")
        assert result["success"] is True

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import filter_tools

        filter_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Filter ID cannot be empty"):
            filter_tools.jira_filter_delete("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.delete_filter.side_effect = ValueError("error")
        filter_tools._client = mock_client
        with pytest.raises(ValueError, match="Filter deletion failed"):
            filter_tools.jira_filter_delete("100")


class TestFilterInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_config = MagicMock()
        filter_tools.initialize_filter_tools(mock_client, mock_config)
        assert filter_tools._client is mock_client
        assert filter_tools._config is mock_config


# ===================== workflow_tools =====================


class TestWorkflowGetTransitions:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        workflow_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            workflow_tools.jira_workflow_get_transitions("TEST-1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        mock_client = _mock_client()
        mock_client.get_transitions.return_value = {
            "transitions": [
                {"id": "1", "name": "Start", "to": {"name": "In Progress"}, "hasScreen": False, "fields": {}}
            ]
        }
        workflow_tools._client = mock_client
        result = workflow_tools.jira_workflow_get_transitions("TEST-1")
        assert result["issue_key"] == "TEST-1"
        assert len(result["transitions"]) == 1
        assert result["transitions"][0]["to_status"] == "In Progress"

    def test_with_fields(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        mock_client = _mock_client()
        mock_client.get_transitions.return_value = {
            "transitions": [
                {
                    "id": "1",
                    "name": "Done",
                    "to": {"name": "Done"},
                    "hasScreen": True,
                    "fields": {"resolution": {"required": True}},
                }
            ]
        }
        workflow_tools._client = mock_client
        result = workflow_tools.jira_workflow_get_transitions("TEST-1")
        assert result["transitions"][0]["fields"] == ["resolution"]

    def test_transition_no_fields(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        mock_client = _mock_client()
        mock_client.get_transitions.return_value = {
            "transitions": [{"id": "1", "name": "Start", "to": {"name": "Open"}, "hasScreen": False}]
        }
        workflow_tools._client = mock_client
        result = workflow_tools.jira_workflow_get_transitions("TEST-1")
        assert result["transitions"][0]["fields"] == []

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        workflow_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            workflow_tools.jira_workflow_get_transitions("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        mock_client = _mock_client()
        mock_client.get_transitions.side_effect = ValueError("error")
        workflow_tools._client = mock_client
        with pytest.raises(ValueError, match="Get transitions failed"):
            workflow_tools.jira_workflow_get_transitions("TEST-1")


class TestWorkflowTransition:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        workflow_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            workflow_tools.jira_workflow_transition("TEST-1", "1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        workflow_tools._client = _mock_client()
        result = workflow_tools.jira_workflow_transition("TEST-1", "1")
        assert result["success"] is True
        assert result["transition_id"] == "1"

    def test_with_fields(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        mock_client = _mock_client()
        workflow_tools._client = mock_client
        workflow_tools.jira_workflow_transition("TEST-1", "1", fields={"resolution": {"name": "Done"}})
        mock_client.transition_issue.assert_called_once_with(
            issue_key="TEST-1", transition_id="1", fields={"resolution": {"name": "Done"}}
        )

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        workflow_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            workflow_tools.jira_workflow_transition("", "1")

    def test_empty_transition_id_raises(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        workflow_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Transition ID cannot be empty"):
            workflow_tools.jira_workflow_transition("TEST-1", "")

    def test_whitespace_transition_id_raises(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        workflow_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Transition ID cannot be empty"):
            workflow_tools.jira_workflow_transition("TEST-1", "  ")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        mock_client = _mock_client()
        mock_client.transition_issue.side_effect = ValueError("error")
        workflow_tools._client = mock_client
        with pytest.raises(ValueError, match="Transition failed"):
            workflow_tools.jira_workflow_transition("TEST-1", "1")


class TestWorkflowInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import workflow_tools

        mock_client = _mock_client()
        workflow_tools.initialize_workflow_tools(mock_client)
        assert workflow_tools._client is mock_client


# ===================== comment_tools =====================


class TestCommentAdd:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            comment_tools.jira_comment_add("TEST-1", "body")

    def test_success(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.add_comment.return_value = {"id": "100", "body": "hello"}
        comment_tools._client = mock_client
        result = comment_tools.jira_comment_add("TEST-1", "hello")
        assert result["id"] == "100"

    def test_body_markdown_converted(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.add_comment.return_value = {"id": "101", "body": "*converted*"}
        comment_tools._client = mock_client
        comment_tools.jira_comment_add("TEST-1", "**bold** and\n- bullet item")
        call_body = mock_client.add_comment.call_args[1]["body"]
        assert call_body == "*bold* and\n* bullet item"

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            comment_tools.jira_comment_add("", "body")

    def test_empty_body_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Comment body cannot be empty"):
            comment_tools.jira_comment_add("TEST-1", "")

    def test_whitespace_body_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Comment body cannot be empty"):
            comment_tools.jira_comment_add("TEST-1", "  ")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.add_comment.side_effect = ValueError("error")
        comment_tools._client = mock_client
        with pytest.raises(ValueError, match="Add comment failed"):
            comment_tools.jira_comment_add("TEST-1", "body")


class TestCommentList:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            comment_tools.jira_comment_list("TEST-1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.list_comments.return_value = {"comments": []}
        comment_tools._client = mock_client
        result = comment_tools.jira_comment_list("TEST-1")
        assert result["comments"] == []

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            comment_tools.jira_comment_list("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.list_comments.side_effect = ValueError("error")
        comment_tools._client = mock_client
        with pytest.raises(ValueError, match="List comments failed"):
            comment_tools.jira_comment_list("TEST-1")


class TestCommentUpdate:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            comment_tools.jira_comment_update("TEST-1", "100", "body")

    def test_success(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.update_comment.return_value = {"id": "100", "body": "new"}
        comment_tools._client = mock_client
        result = comment_tools.jira_comment_update("TEST-1", "100", "new")
        assert result["body"] == "new"

    def test_body_markdown_converted(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.update_comment.return_value = {"id": "100", "body": "updated"}
        comment_tools._client = mock_client
        comment_tools.jira_comment_update("TEST-1", "100", "[link](http://example.com)")
        call_body = mock_client.update_comment.call_args[1]["body"]
        assert call_body == "[link|http://example.com]"

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            comment_tools.jira_comment_update("", "100", "body")

    def test_empty_comment_id_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Comment ID cannot be empty"):
            comment_tools.jira_comment_update("TEST-1", "", "body")

    def test_empty_body_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Comment body cannot be empty"):
            comment_tools.jira_comment_update("TEST-1", "100", "")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.update_comment.side_effect = ValueError("error")
        comment_tools._client = mock_client
        with pytest.raises(ValueError, match="Update comment failed"):
            comment_tools.jira_comment_update("TEST-1", "100", "body")


class TestCommentDelete:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            comment_tools.jira_comment_delete("TEST-1", "100")

    def test_success(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        result = comment_tools.jira_comment_delete("TEST-1", "100")
        assert result["success"] is True

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            comment_tools.jira_comment_delete("", "100")

    def test_empty_comment_id_raises(self) -> None:
        from jira_mcp_server.tools import comment_tools

        comment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Comment ID cannot be empty"):
            comment_tools.jira_comment_delete("TEST-1", "")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.delete_comment.side_effect = ValueError("error")
        comment_tools._client = mock_client
        with pytest.raises(ValueError, match="Delete comment failed"):
            comment_tools.jira_comment_delete("TEST-1", "100")


class TestCommentInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_config = MagicMock()
        comment_tools.initialize_comment_tools(mock_client, mock_config)
        assert comment_tools._client is mock_client
        assert comment_tools._config is mock_config


# ===================== project_tools =====================


class TestProjectList:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import project_tools

        project_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            project_tools.jira_project_list()

    def test_success(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_client.list_projects.return_value = [{"key": "PROJ"}]
        project_tools._client = mock_client
        result = project_tools.jira_project_list()
        assert result[0]["key"] == "PROJ"

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_client.list_projects.side_effect = ValueError("error")
        project_tools._client = mock_client
        with pytest.raises(ValueError, match="List projects failed"):
            project_tools.jira_project_list()


class TestProjectGet:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import project_tools

        project_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            project_tools.jira_project_get("PROJ")

    def test_success(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_client.get_project.return_value = {"key": "PROJ"}
        project_tools._client = mock_client
        result = project_tools.jira_project_get("PROJ")
        assert result["key"] == "PROJ"

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import project_tools

        project_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Project key cannot be empty"):
            project_tools.jira_project_get("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_client.get_project.side_effect = ValueError("error")
        project_tools._client = mock_client
        with pytest.raises(ValueError, match="Get project failed"):
            project_tools.jira_project_get("PROJ")


class TestProjectIssueTypes:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import project_tools

        project_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            project_tools.jira_project_issue_types("PROJ")

    def test_success(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_client.get_issue_types.return_value = [{"name": "Task"}]
        project_tools._client = mock_client
        result = project_tools.jira_project_issue_types("PROJ")
        assert result[0]["name"] == "Task"

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import project_tools

        project_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Project key cannot be empty"):
            project_tools.jira_project_issue_types("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_client.get_issue_types.side_effect = ValueError("error")
        project_tools._client = mock_client
        with pytest.raises(ValueError, match="Get issue types failed"):
            project_tools.jira_project_issue_types("PROJ")


class TestProjectInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_config = MagicMock()
        project_tools.initialize_project_tools(mock_client, mock_config)
        assert project_tools._client is mock_client
        assert project_tools._config is mock_config


# ===================== board_tools =====================


class TestBoardList:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import board_tools

        board_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            board_tools.jira_board_list()

    def test_success(self) -> None:
        from jira_mcp_server.tools import board_tools

        mock_client = _mock_client()
        mock_client.list_boards.return_value = {"values": [{"id": 1}]}
        board_tools._client = mock_client
        result = board_tools.jira_board_list()
        assert result["values"][0]["id"] == 1

    def test_with_project(self) -> None:
        from jira_mcp_server.tools import board_tools

        mock_client = _mock_client()
        mock_client.list_boards.return_value = {"values": []}
        board_tools._client = mock_client
        board_tools.jira_board_list(project_key="PROJ")
        mock_client.list_boards.assert_called_once_with(project_key="PROJ")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import board_tools

        mock_client = _mock_client()
        mock_client.list_boards.side_effect = ValueError("error")
        board_tools._client = mock_client
        with pytest.raises(ValueError, match="List boards failed"):
            board_tools.jira_board_list()


class TestBoardGet:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import board_tools

        board_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            board_tools.jira_board_get("1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import board_tools

        mock_client = _mock_client()
        mock_client.get_board.return_value = {"id": 1}
        board_tools._client = mock_client
        result = board_tools.jira_board_get("1")
        assert result["id"] == 1

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import board_tools

        board_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Board ID cannot be empty"):
            board_tools.jira_board_get("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import board_tools

        mock_client = _mock_client()
        mock_client.get_board.side_effect = ValueError("error")
        board_tools._client = mock_client
        with pytest.raises(ValueError, match="Get board failed"):
            board_tools.jira_board_get("1")


class TestBoardInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import board_tools

        mock_client = _mock_client()
        mock_config = MagicMock()
        board_tools.initialize_board_tools(mock_client, mock_config)
        assert board_tools._client is mock_client
        assert board_tools._config is mock_config


# ===================== sprint_tools =====================


class TestSprintList:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            sprint_tools.jira_sprint_list("1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.list_sprints.return_value = {"values": []}
        sprint_tools._client = mock_client
        result = sprint_tools.jira_sprint_list("1")
        assert result["values"] == []

    def test_with_state(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.list_sprints.return_value = {"values": []}
        sprint_tools._client = mock_client
        sprint_tools.jira_sprint_list("1", state="active")
        mock_client.list_sprints.assert_called_once_with("1", state="active")

    def test_empty_board_id_raises(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Board ID cannot be empty"):
            sprint_tools.jira_sprint_list("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.list_sprints.side_effect = ValueError("error")
        sprint_tools._client = mock_client
        with pytest.raises(ValueError, match="List sprints failed"):
            sprint_tools.jira_sprint_list("1")


class TestSprintGet:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            sprint_tools.jira_sprint_get("1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.get_sprint.return_value = {"id": 1}
        sprint_tools._client = mock_client
        result = sprint_tools.jira_sprint_get("1")
        assert result["id"] == 1

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Sprint ID cannot be empty"):
            sprint_tools.jira_sprint_get("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.get_sprint.side_effect = ValueError("error")
        sprint_tools._client = mock_client
        with pytest.raises(ValueError, match="Get sprint failed"):
            sprint_tools.jira_sprint_get("1")


class TestSprintIssues:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            sprint_tools.jira_sprint_issues("1")

    def test_success(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.get_sprint_issues.return_value = {"issues": [], "total": 0}
        sprint_tools._client = mock_client
        result = sprint_tools.jira_sprint_issues("1")
        assert result["total"] == 0

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Sprint ID cannot be empty"):
            sprint_tools.jira_sprint_issues("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.get_sprint_issues.side_effect = ValueError("error")
        sprint_tools._client = mock_client
        with pytest.raises(ValueError, match="Get sprint issues failed"):
            sprint_tools.jira_sprint_issues("1")


class TestSprintAddIssues:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            sprint_tools.jira_sprint_add_issues("1", ["PROJ-1"])

    def test_success(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.add_issues_to_sprint.return_value = {
            "success": True, "sprint_id": "10", "issues_added": ["PROJ-1"]
        }
        sprint_tools._client = mock_client
        result = sprint_tools.jira_sprint_add_issues("10", ["PROJ-1"])
        assert result["success"] is True
        mock_client.add_issues_to_sprint.assert_called_once_with("10", ["PROJ-1"])

    def test_multiple_issues(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.add_issues_to_sprint.return_value = {
            "success": True, "sprint_id": "10", "issues_added": ["PROJ-1", "PROJ-2"]
        }
        sprint_tools._client = mock_client
        result = sprint_tools.jira_sprint_add_issues("10", ["PROJ-1", "PROJ-2"])
        assert result["issues_added"] == ["PROJ-1", "PROJ-2"]

    def test_empty_issue_keys_raises(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = _mock_client()
        with pytest.raises(ValueError, match="issue_keys must not be empty"):
            sprint_tools.jira_sprint_add_issues("10", [])

    def test_invalid_sprint_id_raises(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = _mock_client()
        with pytest.raises(ValueError, match="must be a numeric string"):
            sprint_tools.jira_sprint_add_issues("abc", ["PROJ-1"])

    def test_invalid_issue_key_raises(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = _mock_client()
        with pytest.raises(ValueError, match="must match format"):
            sprint_tools.jira_sprint_add_issues("10", ["bad-key"])

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.add_issues_to_sprint.side_effect = ValueError("error")
        sprint_tools._client = mock_client
        with pytest.raises(ValueError, match="Add issues to sprint failed"):
            sprint_tools.jira_sprint_add_issues("10", ["PROJ-1"])


class TestSprintRemoveIssues:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            sprint_tools.jira_sprint_remove_issues(["PROJ-1"])

    def test_success(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.remove_issues_from_sprint.return_value = {
            "success": True, "issues_moved_to_backlog": ["PROJ-1"]
        }
        sprint_tools._client = mock_client
        result = sprint_tools.jira_sprint_remove_issues(["PROJ-1"])
        assert result["success"] is True
        mock_client.remove_issues_from_sprint.assert_called_once_with(["PROJ-1"])

    def test_multiple_issues(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.remove_issues_from_sprint.return_value = {
            "success": True, "issues_moved_to_backlog": ["PROJ-1", "PROJ-2"]
        }
        sprint_tools._client = mock_client
        result = sprint_tools.jira_sprint_remove_issues(["PROJ-1", "PROJ-2"])
        assert result["issues_moved_to_backlog"] == ["PROJ-1", "PROJ-2"]

    def test_empty_issue_keys_raises(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = _mock_client()
        with pytest.raises(ValueError, match="issue_keys must not be empty"):
            sprint_tools.jira_sprint_remove_issues([])

    def test_invalid_issue_key_raises(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        sprint_tools._client = _mock_client()
        with pytest.raises(ValueError, match="must match format"):
            sprint_tools.jira_sprint_remove_issues(["bad-key"])

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.remove_issues_from_sprint.side_effect = ValueError("error")
        sprint_tools._client = mock_client
        with pytest.raises(ValueError, match="Remove issues from sprint failed"):
            sprint_tools.jira_sprint_remove_issues(["PROJ-1"])


class TestSprintInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_config = MagicMock()
        sprint_tools.initialize_sprint_tools(mock_client, mock_config)
        assert sprint_tools._client is mock_client
        assert sprint_tools._config is mock_config


# ===================== user_tools =====================


class TestUserSearch:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import user_tools

        user_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            user_tools.jira_user_search("john")

    def test_success(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.search_users.return_value = [{"name": "john"}]
        user_tools._client = mock_client
        result = user_tools.jira_user_search("john")
        assert result[0]["name"] == "john"

    def test_empty_query_raises(self) -> None:
        from jira_mcp_server.tools import user_tools

        user_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            user_tools.jira_user_search("")

    def test_whitespace_query_raises(self) -> None:
        from jira_mcp_server.tools import user_tools

        user_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            user_tools.jira_user_search("  ")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.search_users.side_effect = ValueError("error")
        user_tools._client = mock_client
        with pytest.raises(ValueError, match="User search failed"):
            user_tools.jira_user_search("john")


class TestUserGet:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import user_tools

        user_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            user_tools.jira_user_get("john")

    def test_success(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.get_user.return_value = {"name": "john"}
        user_tools._client = mock_client
        result = user_tools.jira_user_get("john")
        assert result["name"] == "john"

    def test_empty_username_raises(self) -> None:
        from jira_mcp_server.tools import user_tools

        user_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Username cannot be empty"):
            user_tools.jira_user_get("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.get_user.side_effect = ValueError("error")
        user_tools._client = mock_client
        with pytest.raises(ValueError, match="Get user failed"):
            user_tools.jira_user_get("john")


class TestUserMyself:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import user_tools

        user_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            user_tools.jira_user_myself()

    def test_success(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.get_myself.return_value = {"name": "me"}
        user_tools._client = mock_client
        result = user_tools.jira_user_myself()
        assert result["name"] == "me"

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.get_myself.side_effect = ValueError("error")
        user_tools._client = mock_client
        with pytest.raises(ValueError, match="Get current user failed"):
            user_tools.jira_user_myself()


class TestUserInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_config = MagicMock()
        user_tools.initialize_user_tools(mock_client, mock_config)
        assert user_tools._client is mock_client
        assert user_tools._config is mock_config


# ===================== attachment_tools =====================


class TestAttachmentAdd:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            attachment_tools.jira_attachment_add("TEST-1", "/path/file.txt")

    def test_success(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        mock_client = _mock_client()
        mock_client.add_attachment.return_value = [{"id": "100"}]
        attachment_tools._client = mock_client
        result = attachment_tools.jira_attachment_add("TEST-1", "/path/file.txt")
        assert result[0]["id"] == "100"

    def test_with_filename(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        mock_client = _mock_client()
        mock_client.add_attachment.return_value = [{"id": "100"}]
        attachment_tools._client = mock_client
        attachment_tools.jira_attachment_add("TEST-1", "/path/file.txt", filename="custom.txt")
        mock_client.add_attachment.assert_called_once_with("TEST-1", "/path/file.txt", filename="custom.txt")

    def test_empty_key_raises(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Issue key cannot be empty"):
            attachment_tools.jira_attachment_add("", "/path/file.txt")

    def test_empty_path_raises(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="File path cannot be empty"):
            attachment_tools.jira_attachment_add("TEST-1", "")

    def test_whitespace_path_raises(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="File path cannot be empty"):
            attachment_tools.jira_attachment_add("TEST-1", "  ")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        mock_client = _mock_client()
        mock_client.add_attachment.side_effect = ValueError("error")
        attachment_tools._client = mock_client
        with pytest.raises(ValueError, match="Add attachment failed"):
            attachment_tools.jira_attachment_add("TEST-1", "/path/file.txt")


class TestAttachmentGet:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            attachment_tools.jira_attachment_get("100")

    def test_success(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        mock_client = _mock_client()
        mock_client.get_attachment.return_value = {"id": "100"}
        attachment_tools._client = mock_client
        result = attachment_tools.jira_attachment_get("100")
        assert result["id"] == "100"

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Attachment ID cannot be empty"):
            attachment_tools.jira_attachment_get("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        mock_client = _mock_client()
        mock_client.get_attachment.side_effect = ValueError("error")
        attachment_tools._client = mock_client
        with pytest.raises(ValueError, match="Get attachment failed"):
            attachment_tools.jira_attachment_get("100")


class TestAttachmentDelete:
    def test_not_initialized(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            attachment_tools.jira_attachment_delete("100")

    def test_success(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = _mock_client()
        result = attachment_tools.jira_attachment_delete("100")
        assert result["success"] is True

    def test_empty_id_raises(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        attachment_tools._client = _mock_client()
        with pytest.raises(ValueError, match="Attachment ID cannot be empty"):
            attachment_tools.jira_attachment_delete("")

    def test_client_failure(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        mock_client = _mock_client()
        mock_client.delete_attachment.side_effect = ValueError("error")
        attachment_tools._client = mock_client
        with pytest.raises(ValueError, match="Delete attachment failed"):
            attachment_tools.jira_attachment_delete("100")


class TestAttachmentInitialize:
    def test_initialize(self) -> None:
        from jira_mcp_server.tools import attachment_tools

        mock_client = _mock_client()
        attachment_tools.initialize_attachment_tools(mock_client)
        assert attachment_tools._client is mock_client


# ===================== detail parameter tests =====================


def _summary_config() -> MagicMock:
    config = MagicMock()
    config.default_detail = "summary"
    config.max_description_length = 500
    config.include_links = False
    config.summary_fields = None
    return config


class TestIssueGetDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import issue_tools

        mock_client = _mock_client()
        mock_client.get_issue.return_value = {
            "key": "PROJ-1",
            "fields": {
                "summary": "Test",
                "status": {"name": "Open"},
                "assignee": None,
                "priority": {"name": "Medium"},
                "issuetype": {"name": "Task"},
                "labels": [],
                "components": [],
                "resolution": None,
                "description": None,
                "created": "2024-01-01",
                "updated": "2024-01-02",
                "duedate": None,
            },
        }
        issue_tools._client = mock_client
        issue_tools._config = _summary_config()
        result = issue_tools.jira_issue_get("PROJ-1", detail="summary")
        assert result["key"] == "PROJ-1"
        assert result["status"] == "Open"
        assert "fields" not in result
        mock_client.get_issue.assert_called_once()
        call_args = mock_client.get_issue.call_args
        assert call_args[1].get("fields") is not None


class TestSearchIssuesDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import search_tools

        mock_client = _mock_client()
        mock_client.search_issues.return_value = {
            "total": 1, "startAt": 0, "maxResults": 50,
            "issues": [{"key": "PROJ-1", "fields": {"summary": "Test"}}],
        }
        search_tools._client = mock_client
        search_tools._config = _summary_config()
        result = search_tools.jira_search_issues(project="TEST", detail="summary")
        assert result["total"] == 1
        assert result["issues"][0]["key"] == "PROJ-1"
        assert "fields" not in result["issues"][0]


class TestSearchJqlDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import search_tools

        mock_client = _mock_client()
        mock_client.search_issues.return_value = {
            "total": 0, "startAt": 0, "maxResults": 50, "issues": [],
        }
        search_tools._client = mock_client
        search_tools._config = _summary_config()
        result = search_tools.jira_search_jql("project = TEST", detail="summary")
        assert result["total"] == 0
        assert result["issues"] == []


class TestFilterExecuteDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import filter_tools

        mock_client = _mock_client()
        mock_client.get_filter.return_value = {"jql": "project = TEST"}
        mock_client.search_issues.return_value = {
            "total": 1, "startAt": 0, "maxResults": 50,
            "issues": [{"key": "PROJ-1", "fields": {"summary": "Test"}}],
        }
        filter_tools._client = mock_client
        filter_tools._config = _summary_config()
        result = filter_tools.jira_filter_execute("123", detail="summary")
        assert result["total"] == 1
        assert "fields" not in result["issues"][0]


class TestCommentListDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import comment_tools

        mock_client = _mock_client()
        mock_client.list_comments.return_value = {
            "total": 1,
            "comments": [{"id": "1", "body": "hello", "author": {"name": "troy"}}],
        }
        comment_tools._client = mock_client
        comment_tools._config = _summary_config()
        result = comment_tools.jira_comment_list("PROJ-1", detail="summary")
        assert result["total"] == 1
        assert result["comments"][0]["author"] == "troy"


class TestProjectListDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_client.list_projects.return_value = [
            {"key": "PROJ", "name": "Project", "self": "https://jira/p/1"},
        ]
        project_tools._client = mock_client
        project_tools._config = _summary_config()
        result = project_tools.jira_project_list(detail="summary")
        assert result[0]["key"] == "PROJ"
        assert "self" not in result[0]


class TestProjectGetDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import project_tools

        mock_client = _mock_client()
        mock_client.get_project.return_value = {
            "key": "PROJ", "name": "Project", "self": "https://jira/p/1",
        }
        project_tools._client = mock_client
        project_tools._config = _summary_config()
        result = project_tools.jira_project_get("PROJ", detail="summary")
        assert result["key"] == "PROJ"
        assert "self" not in result


class TestBoardGetDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import board_tools

        mock_client = _mock_client()
        mock_client.get_board.return_value = {
            "id": 1, "name": "Board", "type": "scrum", "self": "https://jira/b/1",
        }
        board_tools._client = mock_client
        board_tools._config = _summary_config()
        result = board_tools.jira_board_get("1", detail="summary")
        assert result["id"] == 1
        assert "self" not in result


class TestSprintGetDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.get_sprint.return_value = {
            "id": 42, "name": "Sprint 1", "state": "active", "self": "https://jira/s/42",
        }
        sprint_tools._client = mock_client
        sprint_tools._config = _summary_config()
        result = sprint_tools.jira_sprint_get("42", detail="summary")
        assert result["id"] == 42
        assert "self" not in result


class TestSprintIssuesDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import sprint_tools

        mock_client = _mock_client()
        mock_client.get_sprint_issues.return_value = {
            "total": 1, "startAt": 0, "maxResults": 50,
            "issues": [{"key": "PROJ-1", "fields": {"summary": "Test"}}],
        }
        sprint_tools._client = mock_client
        sprint_tools._config = _summary_config()
        result = sprint_tools.jira_sprint_issues("42", detail="summary")
        assert result["total"] == 1
        assert "fields" not in result["issues"][0]


class TestUserSearchDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.search_users.return_value = [
            {"name": "troy", "displayName": "Troy", "self": "https://jira/u/1"},
        ]
        user_tools._client = mock_client
        user_tools._config = _summary_config()
        result = user_tools.jira_user_search("troy", detail="summary")
        assert result[0]["displayName"] == "Troy"
        assert "self" not in result[0]


class TestUserGetDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.get_user.return_value = {
            "name": "troy", "displayName": "Troy", "self": "https://jira/u/1",
        }
        user_tools._client = mock_client
        user_tools._config = _summary_config()
        result = user_tools.jira_user_get("troy", detail="summary")
        assert result["displayName"] == "Troy"
        assert "self" not in result


class TestUserMyselfDetail:
    def test_summary_mode(self) -> None:
        from jira_mcp_server.tools import user_tools

        mock_client = _mock_client()
        mock_client.get_myself.return_value = {
            "name": "troy", "displayName": "Troy", "self": "https://jira/u/1",
        }
        user_tools._client = mock_client
        user_tools._config = _summary_config()
        result = user_tools.jira_user_myself(detail="summary")
        assert result["displayName"] == "Troy"
        assert "self" not in result
