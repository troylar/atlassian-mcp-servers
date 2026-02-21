"""Tests for Pydantic models."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from jira_mcp_server.models import (
    CachedSchema,
    Comment,
    FieldSchema,
    FieldType,
    FieldValidationError,
    Filter,
    Issue,
    JiraAPIError,
    Project,
    SearchResult,
    WorkflowTransition,
)


class TestFieldSchema:
    def test_valid_identifier_key(self) -> None:
        schema = FieldSchema(key="summary", name="Summary", type=FieldType.STRING, required=True, custom=False)
        assert schema.key == "summary"

    def test_valid_customfield_key(self) -> None:
        schema = FieldSchema(
            key="customfield_10001", name="Custom", type=FieldType.STRING, required=False, custom=True
        )
        assert schema.key == "customfield_10001"

    def test_invalid_key_raises(self) -> None:
        with pytest.raises(ValidationError, match="Invalid field key"):
            FieldSchema(key="123-bad", name="Bad", type=FieldType.STRING, required=False, custom=False)

    def test_allowed_values(self) -> None:
        schema = FieldSchema(
            key="priority",
            name="Priority",
            type=FieldType.OPTION,
            required=False,
            custom=False,
            allowed_values=["High", "Medium", "Low"],
        )
        assert schema.allowed_values == ["High", "Medium", "Low"]

    def test_schema_type(self) -> None:
        schema = FieldSchema(
            key="summary",
            name="Summary",
            type=FieldType.STRING,
            required=True,
            custom=False,
            schema_type="string",
        )
        assert schema.schema_type == "string"

    def test_all_field_types(self) -> None:
        for ft in FieldType:
            schema = FieldSchema(key="test", name="Test", type=ft, required=False, custom=False)
            assert schema.type == ft


class TestIssue:
    def test_valid_issue(self) -> None:
        issue = Issue(
            key="TEST-123",
            id="10001",
            self="https://jira.example.com/rest/api/2/issue/10001",
            project="TEST",
            issue_type="Task",
            summary="Test issue",
            status="Open",
            created=datetime(2024, 1, 1),
            updated=datetime(2024, 1, 2),
        )
        assert issue.key == "TEST-123"

    def test_invalid_key_pattern(self) -> None:
        with pytest.raises(ValidationError):
            Issue(
                key="bad-key",
                id="10001",
                self="https://jira.example.com/rest/api/2/issue/10001",
                project="TEST",
                issue_type="Task",
                summary="Test",
                status="Open",
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 2),
            )

    def test_empty_summary_raises(self) -> None:
        with pytest.raises(ValidationError):
            Issue(
                key="TEST-1",
                id="10001",
                self="https://jira.example.com/rest/api/2/issue/10001",
                project="TEST",
                issue_type="Task",
                summary="",
                status="Open",
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 2),
            )

    def test_optional_fields_default(self) -> None:
        issue = Issue(
            key="TEST-1",
            id="10001",
            self="https://jira.example.com/rest/api/2/issue/10001",
            project="TEST",
            issue_type="Task",
            summary="Test",
            status="Open",
            created=datetime(2024, 1, 1),
            updated=datetime(2024, 1, 2),
        )
        assert issue.description is None
        assert issue.priority is None
        assert issue.assignee is None
        assert issue.reporter is None
        assert issue.due_date is None
        assert issue.labels == []
        assert issue.custom_fields == {}

    def test_all_optional_fields(self) -> None:
        issue = Issue(
            key="TEST-1",
            id="10001",
            self="https://jira.example.com/rest/api/2/issue/10001",
            project="TEST",
            issue_type="Task",
            summary="Test",
            status="Open",
            created=datetime(2024, 1, 1),
            updated=datetime(2024, 1, 2),
            description="desc",
            priority="High",
            assignee="john",
            reporter="jane",
            due_date=date(2024, 12, 31),
            labels=["bug"],
            custom_fields={"cf_1": "val"},
        )
        assert issue.description == "desc"
        assert issue.due_date == date(2024, 12, 31)


class TestProject:
    def test_valid_project(self) -> None:
        proj = Project(
            key="PROJ",
            id="10000",
            name="Project",
            self="https://jira.example.com/rest/api/2/project/10000",
            issue_types=["Task"],
        )
        assert proj.key == "PROJ"

    def test_invalid_project_key(self) -> None:
        with pytest.raises(ValidationError):
            Project(
                key="bad",
                id="10000",
                name="Project",
                self="https://jira.example.com/rest/api/2/project/10000",
                issue_types=["Task"],
            )


class TestSearchResult:
    def test_valid_search_result(self) -> None:
        sr = SearchResult(total=0, max_results=50, start_at=0, issues=[])
        assert sr.total == 0
        assert sr.issues == []


class TestCachedSchema:
    def test_valid_cached_schema(self) -> None:
        now = datetime.now()
        cs = CachedSchema(
            project_key="PROJ",
            issue_type="Task",
            fields=[],
            cached_at=now,
            expires_at=now,
        )
        assert cs.project_key == "PROJ"


class TestFilter:
    def test_valid_filter(self) -> None:
        f = Filter(id="100", name="My Filter", jql="project = TEST", owner="admin")
        assert f.name == "My Filter"
        assert f.favourite is False
        assert f.share_permissions == []

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            Filter(id="100", name="", jql="project = TEST", owner="admin")

    def test_empty_jql_raises(self) -> None:
        with pytest.raises(ValidationError):
            Filter(id="100", name="Filter", jql="", owner="admin")


class TestWorkflowTransition:
    def test_valid_transition(self) -> None:
        wt = WorkflowTransition(id="1", name="Start", to_status="In Progress", has_screen=False)
        assert wt.required_fields == []

    def test_with_required_fields(self) -> None:
        wt = WorkflowTransition(
            id="1", name="Start", to_status="In Progress", has_screen=True, required_fields=["resolution"]
        )
        assert wt.required_fields == ["resolution"]


class TestComment:
    def test_valid_comment(self) -> None:
        c = Comment(
            id="10000",
            author="admin",
            body="Hello",
            created=datetime(2024, 1, 1),
            updated=datetime(2024, 1, 1),
        )
        assert c.visibility is None

    def test_empty_body_raises(self) -> None:
        with pytest.raises(ValidationError):
            Comment(
                id="10000",
                author="admin",
                body="",
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 1),
            )


class TestExceptions:
    def test_jira_api_error(self) -> None:
        err = JiraAPIError("Test error", jira_errors=["err1", "err2"])
        assert str(err) == "Test error"
        assert err.jira_errors == ["err1", "err2"]

    def test_jira_api_error_no_errors(self) -> None:
        err = JiraAPIError("Test error")
        assert err.jira_errors == []

    def test_field_validation_error(self) -> None:
        err = FieldValidationError("summary", "is required")
        assert err.field_name == "summary"
        assert err.reason == "is required"
        assert "summary" in str(err)
        assert "is required" in str(err)
