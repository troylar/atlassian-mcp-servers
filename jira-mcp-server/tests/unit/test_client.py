"""Tests for JiraClient."""

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import AuthType, JiraConfig


def _make_config(auth_type: AuthType = AuthType.PAT) -> JiraConfig:
    if auth_type == AuthType.CLOUD:
        return JiraConfig(
            url="https://company.atlassian.net",
            token="api-token",
            email="user@company.com",
            auth_type=AuthType.CLOUD,
        )
    return JiraConfig(
        url="https://jira.example.com",
        token="test-pat-token",
        auth_type=AuthType.PAT,
    )


def _mock_response(status_code: int = 200, json_data: object = None, text: str = "") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text or ""
    resp.request = MagicMock()
    resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1"
    return resp


class TestAuthHeaders:
    def test_bearer_auth_for_pat(self) -> None:
        client = JiraClient(_make_config(AuthType.PAT))
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-pat-token"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_basic_auth_for_cloud(self) -> None:
        client = JiraClient(_make_config(AuthType.CLOUD))
        headers = client._get_headers()
        expected = base64.b64encode(b"user@company.com:api-token").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_default_auth_type_pat_when_none(self) -> None:
        config = _make_config(AuthType.PAT)
        config._auth_type = None  # type: ignore[assignment]
        client = JiraClient(config)
        client._auth_type = AuthType.PAT
        headers = client._get_headers()
        assert "Bearer" in headers["Authorization"]


class TestHealthCheck:
    def test_health_check_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"version": "9.0.0", "baseUrl": "https://jira.example.com"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.health_check()
        assert result["connected"] is True
        assert result["server_version"] == "9.0.0"
        assert result["base_url"] == "https://jira.example.com"
        assert result["auth_type"] == "pat"

    def test_health_check_error_status(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.health_check()

    def test_health_check_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Connection timeout"):
                client.health_check()

    def test_health_check_network_error(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.NetworkError("dns fail")):
            with pytest.raises(ValueError, match="Network error"):
                client.health_check()

    def test_health_check_missing_version(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.health_check()
        assert result["server_version"] == "unknown"


class TestIssueOperations:
    def test_get_issue_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"key": "TEST-1", "fields": {}})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_issue("TEST-1")
        assert result["key"] == "TEST-1"

    def test_get_issue_not_found(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Issue TEST-1 not found"):
                client.get_issue("TEST-1")

    def test_get_issue_other_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(500, text="Internal server error")
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Jira API error"):
                client.get_issue("TEST-1")

    def test_get_issue_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting issue TEST-1"):
                client.get_issue("TEST-1")

    def test_create_issue_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(201, {"key": "TEST-2", "id": "10001"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.create_issue({"fields": {"summary": "test"}})
        assert result["key"] == "TEST-2"

    def test_create_issue_200(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"key": "TEST-2"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.create_issue({"fields": {"summary": "test"}})
        assert result["key"] == "TEST-2"

    def test_create_issue_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(400, {"errors": {"summary": "required"}, "errorMessages": []}, text="bad")
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Validation error"):
                client.create_issue({"fields": {}})

    def test_create_issue_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout creating issue"):
                client.create_issue({"fields": {}})

    def test_update_issue_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp):
            client.update_issue("TEST-1", {"fields": {"summary": "updated"}})

    def test_update_issue_200(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200)
        with patch.object(client, "_request", return_value=mock_resp):
            client.update_issue("TEST-1", {"fields": {"summary": "updated"}})

    def test_update_issue_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(403)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.update_issue("TEST-1", {"fields": {}})

    def test_update_issue_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout updating issue"):
                client.update_issue("TEST-1", {"fields": {}})

    def test_delete_issue_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp):
            client.delete_issue("TEST-1")

    def test_delete_issue_with_subtasks(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.delete_issue("TEST-1", delete_subtasks=True)
        call_kwargs = mock_req.call_args
        assert call_kwargs[1]["params"]["deleteSubtasks"] == "true"

    def test_delete_issue_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.delete_issue("TEST-1")

    def test_delete_issue_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout deleting issue"):
                client.delete_issue("TEST-1")


class TestLinkIssues:
    def test_link_issues_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(201)
        with patch.object(client, "_request", return_value=mock_resp):
            client.link_issues("Blocks", "TEST-1", "TEST-2")

    def test_link_issues_200(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200)
        with patch.object(client, "_request", return_value=mock_resp):
            client.link_issues("Blocks", "TEST-1", "TEST-2")

    def test_link_issues_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(400, {"errorMessages": ["invalid link"]}, text="bad")
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issueLink"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Validation error"):
                client.link_issues("BadType", "TEST-1", "TEST-2")

    def test_link_issues_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout linking issues"):
                client.link_issues("Blocks", "TEST-1", "TEST-2")


class TestProjectSchema:
    def test_get_project_schema_success(self) -> None:
        client = JiraClient(_make_config())
        schema_data = {
            "projects": [
                {
                    "issuetypes": [
                        {
                            "fields": {
                                "summary": {"name": "Summary", "required": True, "schema": {"type": "string"}},
                            }
                        }
                    ]
                }
            ]
        }
        mock_resp = _mock_response(200, schema_data)
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_project_schema("PROJ", "Task")
        assert len(result) == 1
        assert result[0]["key"] == "summary"

    def test_get_project_schema_404(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Project schema not found"):
                client.get_project_schema("PROJ", "Task")

    def test_get_project_schema_no_projects(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"projects": []})
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="returned no data"):
                client.get_project_schema("PROJ", "Task")

    def test_get_project_schema_no_issue_types(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"projects": [{"issuetypes": []}]})
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Issue type.*not found"):
                client.get_project_schema("PROJ", "Task")

    def test_get_project_schema_other_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(500, text="server error")
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/createmeta"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Jira API error"):
                client.get_project_schema("PROJ", "Task")

    def test_get_project_schema_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting schema"):
                client.get_project_schema("PROJ", "Task")


class TestSearchIssues:
    def test_search_issues_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"issues": [], "total": 0})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.search_issues("project = TEST")
        assert result["total"] == 0

    def test_search_issues_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(400, {"errorMessages": ["bad jql"]}, text="bad")
        mock_resp.request.url = "https://jira.example.com/rest/api/2/search"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Validation error"):
                client.search_issues("bad jql")

    def test_search_issues_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout executing search"):
                client.search_issues("project = TEST")


class TestFilterOperations:
    def test_create_filter_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(201, {"id": "100", "name": "My Filter"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.create_filter("My Filter", "project = TEST")
        assert result["id"] == "100"

    def test_create_filter_200(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": "100"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.create_filter("My Filter", "project = TEST")
        assert result["id"] == "100"

    def test_create_filter_with_description(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(201, {"id": "100"})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.create_filter("My Filter", "project = TEST", description="desc", favourite=True)
        call_data = mock_req.call_args[1]["json"]
        assert call_data["description"] == "desc"
        assert call_data["favourite"] is True

    def test_create_filter_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(400, text="bad request")
        mock_resp.request.url = "https://jira.example.com/rest/api/2/filter"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Bad request"):
                client.create_filter("", "")

    def test_create_filter_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout creating filter"):
                client.create_filter("My Filter", "project = TEST")

    def test_list_filters_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, [{"id": "100"}, {"id": "101"}])
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.list_filters()
        assert len(result) == 2

    def test_list_filters_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/filter/my"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_filters()

    def test_list_filters_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout listing filters"):
                client.list_filters()

    def test_get_filter_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": "100", "jql": "project = TEST"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_filter("100")
        assert result["jql"] == "project = TEST"

    def test_get_filter_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/filter/999"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found.*filter"):
                client.get_filter("999")

    def test_get_filter_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting filter"):
                client.get_filter("100")

    def test_update_filter_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": "100", "name": "Updated"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.update_filter("100", name="Updated")
        assert result["name"] == "Updated"

    def test_update_filter_all_fields(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": "100"})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.update_filter("100", name="n", jql="j", description="d", favourite=True)
        call_data = mock_req.call_args[1]["json"]
        assert call_data == {"name": "n", "jql": "j", "description": "d", "favourite": True}

    def test_update_filter_no_fields_raises(self) -> None:
        client = JiraClient(_make_config())
        with pytest.raises(ValueError, match="At least one field"):
            client.update_filter("100")

    def test_update_filter_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(400, text="bad")
        mock_resp.request.url = "https://jira.example.com/rest/api/2/filter/100"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Bad request"):
                client.update_filter("100", name="x")

    def test_update_filter_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout updating filter"):
                client.update_filter("100", name="x")

    def test_delete_filter_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp):
            client.delete_filter("100")

    def test_delete_filter_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/filter/999"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.delete_filter("999")

    def test_delete_filter_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout deleting filter"):
                client.delete_filter("100")


class TestWorkflowOperations:
    def test_get_transitions_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"transitions": [{"id": "1", "name": "Start"}]})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_transitions("TEST-1")
        assert len(result["transitions"]) == 1

    def test_get_transitions_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/transitions"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_transitions("TEST-1")

    def test_get_transitions_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting transitions"):
                client.get_transitions("TEST-1")

    def test_transition_issue_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp):
            client.transition_issue("TEST-1", "21")

    def test_transition_issue_with_fields(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.transition_issue("TEST-1", "21", fields={"resolution": {"name": "Done"}})
        call_data = mock_req.call_args[1]["json"]
        assert call_data["fields"] == {"resolution": {"name": "Done"}}

    def test_transition_issue_no_fields(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.transition_issue("TEST-1", "21")
        call_data = mock_req.call_args[1]["json"]
        assert "fields" not in call_data

    def test_transition_issue_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(400, text="bad")
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/transitions"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Bad request"):
                client.transition_issue("TEST-1", "999")

    def test_transition_issue_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout transitioning issue"):
                client.transition_issue("TEST-1", "21")


class TestCommentOperations:
    def test_add_comment_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(201, {"id": "10000", "body": "hello"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.add_comment("TEST-1", "hello")
        assert result["id"] == "10000"

    def test_add_comment_200(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": "10000"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.add_comment("TEST-1", "hello")
        assert result["id"] == "10000"

    def test_add_comment_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/comment"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.add_comment("TEST-1", "hello")

    def test_add_comment_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout adding comment"):
                client.add_comment("TEST-1", "hello")

    def test_list_comments_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"comments": [{"id": "1"}]})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.list_comments("TEST-1")
        assert len(result["comments"]) == 1

    def test_list_comments_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/comment"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_comments("TEST-1")

    def test_list_comments_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout listing comments"):
                client.list_comments("TEST-1")

    def test_update_comment_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": "10000", "body": "updated"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.update_comment("TEST-1", "10000", "updated")
        assert result["body"] == "updated"

    def test_update_comment_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(403)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/comment/10000"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.update_comment("TEST-1", "10000", "updated")

    def test_update_comment_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout updating comment"):
                client.update_comment("TEST-1", "10000", "updated")

    def test_delete_comment_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp):
            client.delete_comment("TEST-1", "10000")

    def test_delete_comment_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/comment/10000"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.delete_comment("TEST-1", "10000")

    def test_delete_comment_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout deleting comment"):
                client.delete_comment("TEST-1", "10000")


class TestProjectOperations:
    def test_list_projects_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, [{"key": "PROJ"}])
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.list_projects()
        assert result[0]["key"] == "PROJ"

    def test_list_projects_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/project"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_projects()

    def test_list_projects_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout listing projects"):
                client.list_projects()

    def test_get_project_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"key": "PROJ", "name": "Test"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_project("PROJ")
        assert result["name"] == "Test"

    def test_get_project_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/project/NOPE"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found.*project"):
                client.get_project("NOPE")

    def test_get_project_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting project"):
                client.get_project("PROJ")

    def test_get_issue_types_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, [{"name": "Task"}])
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_issue_types("PROJ")
        assert result[0]["name"] == "Task"

    def test_get_issue_types_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/project/PROJ/statuses"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_issue_types("PROJ")

    def test_get_issue_types_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting issue types"):
                client.get_issue_types("PROJ")


class TestBoardOperations:
    def test_list_boards_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"values": [{"id": 1}]})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.list_boards()
        assert result["values"][0]["id"] == 1

    def test_list_boards_with_project(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"values": []})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.list_boards(project_key="PROJ")
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["params"]["projectKeyOrId"] == "PROJ"

    def test_list_boards_without_project(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"values": []})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.list_boards()
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["params"] == {}

    def test_list_boards_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/agile/1.0/board"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_boards()

    def test_list_boards_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout listing boards"):
                client.list_boards()

    def test_get_board_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": 1, "name": "Board 1"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_board("1")
        assert result["name"] == "Board 1"

    def test_get_board_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/agile/1.0/board/999"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found.*board"):
                client.get_board("999")

    def test_get_board_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting board"):
                client.get_board("1")


class TestSprintOperations:
    def test_list_sprints_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"values": [{"id": 1}]})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.list_sprints("1")
        assert len(result["values"]) == 1

    def test_list_sprints_with_state(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"values": []})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.list_sprints("1", state="active")
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["params"]["state"] == "active"

    def test_list_sprints_without_state(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"values": []})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.list_sprints("1")
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["params"] == {}

    def test_list_sprints_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/agile/1.0/board/1/sprint"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.list_sprints("1")

    def test_list_sprints_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout listing sprints"):
                client.list_sprints("1")

    def test_get_sprint_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": 1, "name": "Sprint 1"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_sprint("1")
        assert result["name"] == "Sprint 1"

    def test_get_sprint_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/agile/1.0/sprint/999"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found.*sprint"):
                client.get_sprint("999")

    def test_get_sprint_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting sprint"):
                client.get_sprint("1")

    def test_get_sprint_issues_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"issues": [{"key": "TEST-1"}], "total": 1})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_sprint_issues("1")
        assert result["total"] == 1

    def test_get_sprint_issues_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/agile/1.0/sprint/1/issue"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_sprint_issues("1")

    def test_get_sprint_issues_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting issues for sprint"):
                client.get_sprint_issues("1")

    def test_add_issues_to_sprint_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            result = client.add_issues_to_sprint("10", ["PROJ-1", "PROJ-2"])
        assert result["success"] is True
        assert result["sprint_id"] == "10"
        assert result["issues_added"] == ["PROJ-1", "PROJ-2"]
        call_args = mock_req.call_args
        assert call_args[0] == ("POST", "https://jira.example.com/rest/agile/1.0/sprint/10/issue")
        assert call_args[1]["json"] == {"issues": ["PROJ-1", "PROJ-2"]}

    def test_add_issues_to_sprint_200(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200)
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.add_issues_to_sprint("10", ["PROJ-1"])
        assert result["success"] is True

    def test_add_issues_to_sprint_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(400, json_data={"errorMessages": ["Invalid issue"]})
        mock_resp.request.url = "https://jira.example.com/rest/agile/1.0/sprint/10/issue"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError):
                client.add_issues_to_sprint("10", ["BAD-1"])

    def test_add_issues_to_sprint_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout adding issues to sprint"):
                client.add_issues_to_sprint("10", ["PROJ-1"])

    def test_remove_issues_from_sprint_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            result = client.remove_issues_from_sprint(["PROJ-1", "PROJ-3"])
        assert result["success"] is True
        assert result["issues_moved_to_backlog"] == ["PROJ-1", "PROJ-3"]
        call_args = mock_req.call_args
        assert call_args[0] == ("POST", "https://jira.example.com/rest/agile/1.0/backlog/issue")
        assert call_args[1]["json"] == {"issues": ["PROJ-1", "PROJ-3"]}

    def test_remove_issues_from_sprint_200(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200)
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.remove_issues_from_sprint(["PROJ-1"])
        assert result["success"] is True

    def test_remove_issues_from_sprint_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/agile/1.0/backlog/issue"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.remove_issues_from_sprint(["BAD-1"])

    def test_remove_issues_from_sprint_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout removing issues from sprint"):
                client.remove_issues_from_sprint(["PROJ-1"])


class TestUserOperations:
    def test_search_users_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, [{"name": "john"}])
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.search_users("john")
        assert result[0]["name"] == "john"

    def test_search_users_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/user/search"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.search_users("john")

    def test_search_users_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout searching users"):
                client.search_users("john")

    def test_get_user_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"name": "john", "displayName": "John"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_user("john")
        assert result["displayName"] == "John"

    def test_get_user_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/user?username=nobody"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found.*user"):
                client.get_user("nobody")

    def test_get_user_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting user"):
                client.get_user("john")

    def test_get_myself_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"name": "me", "emailAddress": "me@co.com"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_myself()
        assert result["name"] == "me"

    def test_get_myself_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/myself"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.get_myself()

    def test_get_myself_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting current user"):
                client.get_myself()


class TestAttachmentOperations:
    def test_add_attachment_success(self, tmp_path: Path) -> None:
        client = JiraClient(_make_config())
        f = tmp_path / "test.txt"
        f.write_bytes(b"file content")
        mock_resp = _mock_response(201, [{"id": "10000", "filename": "test.txt"}])
        with patch("httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.post.return_value = mock_resp
            result = client.add_attachment("TEST-1", str(f))
        assert result[0]["filename"] == "test.txt"

    def test_add_attachment_with_custom_filename(self, tmp_path: Path) -> None:
        client = JiraClient(_make_config())
        f = tmp_path / "test.txt"
        f.write_bytes(b"file content")
        mock_resp = _mock_response(200, [{"id": "10000", "filename": "custom.txt"}])
        with patch("httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.post.return_value = mock_resp
            result = client.add_attachment("TEST-1", str(f), filename="custom.txt")
        assert result[0]["filename"] == "custom.txt"

    def test_add_attachment_error(self, tmp_path: Path) -> None:
        client = JiraClient(_make_config())
        f = tmp_path / "test.txt"
        f.write_bytes(b"data")
        mock_resp = _mock_response(403)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/attachments"
        with patch("httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.post.return_value = mock_resp
            with pytest.raises(ValueError, match="Permission denied"):
                client.add_attachment("TEST-1", str(f))

    def test_add_attachment_timeout(self, tmp_path: Path) -> None:
        client = JiraClient(_make_config())
        f = tmp_path / "test.txt"
        f.write_bytes(b"data")
        with patch("httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.post.side_effect = httpx.TimeoutException("timeout")
            with pytest.raises(ValueError, match="Timeout adding attachment"):
                client.add_attachment("TEST-1", str(f))

    def test_add_attachment_file_not_found(self) -> None:
        client = JiraClient(_make_config())
        with pytest.raises(ValueError, match="File not found"):
            client.add_attachment("TEST-1", "/nonexistent/file.txt")

    def test_get_attachment_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": "10000", "filename": "test.txt"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.get_attachment("10000")
        assert result["filename"] == "test.txt"

    def test_get_attachment_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/attachment/999"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_attachment("999")

    def test_get_attachment_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout getting attachment"):
                client.get_attachment("10000")

    def test_delete_attachment_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp):
            client.delete_attachment("10000")

    def test_delete_attachment_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/attachment/999"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.delete_attachment("999")

    def test_delete_attachment_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout deleting attachment"):
                client.delete_attachment("10000")


class TestDownloadAttachment:
    def test_download_text_file(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10000",
            "filename": "readme.txt",
            "mimeType": "text/plain",
            "size": 13,
            "content": "https://jira.example.com/secure/attachment/10000/readme.txt",
        }
        mock_meta_resp = _mock_response(200, metadata)
        mock_download_resp = MagicMock(spec=httpx.Response)
        mock_download_resp.status_code = 200
        mock_download_resp.content = b"Hello, World!"
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.return_value = mock_download_resp
                result = client.download_attachment("10000")
        assert result["content"] == "Hello, World!"
        assert result["encoding"] == "text"
        assert result["filename"] == "readme.txt"
        assert result["size"] == 13
        assert result["mime_type"] == "text/plain"

    def test_download_binary_file(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10001",
            "filename": "image.png",
            "mimeType": "image/png",
            "size": 4,
            "content": "https://jira.example.com/secure/attachment/10001/image.png",
        }
        mock_meta_resp = _mock_response(200, metadata)
        mock_download_resp = MagicMock(spec=httpx.Response)
        mock_download_resp.status_code = 200
        mock_download_resp.content = b"\x89PNG"
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.return_value = mock_download_resp
                result = client.download_attachment("10001")
        import base64

        assert result["content"] == base64.b64encode(b"\x89PNG").decode("ascii")
        assert result["encoding"] == "base64"
        assert result["filename"] == "image.png"
        assert result["mime_type"] == "image/png"

    def test_download_json_file_is_text(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10002",
            "filename": "data.json",
            "mimeType": "application/json",
            "size": 2,
            "content": "https://jira.example.com/secure/attachment/10002/data.json",
        }
        mock_meta_resp = _mock_response(200, metadata)
        mock_download_resp = MagicMock(spec=httpx.Response)
        mock_download_resp.status_code = 200
        mock_download_resp.content = b"{}"
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.return_value = mock_download_resp
                result = client.download_attachment("10002")
        assert result["encoding"] == "text"

    def test_download_no_content_url(self) -> None:
        client = JiraClient(_make_config())
        metadata = {"id": "10000", "filename": "test.txt", "mimeType": "text/plain", "size": 5}
        mock_meta_resp = _mock_response(200, metadata)
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with pytest.raises(ValueError, match="No download URL found"):
                client.download_attachment("10000")

    def test_download_size_exceeds_limit_from_metadata(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10000",
            "filename": "huge.bin",
            "mimeType": "application/octet-stream",
            "size": 20_000_000,
            "content": "https://jira.example.com/secure/attachment/10000/huge.bin",
        }
        mock_meta_resp = _mock_response(200, metadata)
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with pytest.raises(ValueError, match="exceeds.*byte limit"):
                client.download_attachment("10000")

    def test_download_size_exceeds_limit_from_actual(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10000",
            "filename": "sneaky.bin",
            "mimeType": "application/octet-stream",
            "size": 100,
            "content": "https://jira.example.com/secure/attachment/10000/sneaky.bin",
        }
        mock_meta_resp = _mock_response(200, metadata)
        mock_download_resp = MagicMock(spec=httpx.Response)
        mock_download_resp.status_code = 200
        mock_download_resp.content = b"x" * 200
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.return_value = mock_download_resp
                with pytest.raises(ValueError, match="exceeds.*byte limit"):
                    client.download_attachment("10000", max_size=150)

    def test_download_custom_max_size(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10000",
            "filename": "small.txt",
            "mimeType": "text/plain",
            "size": 5,
            "content": "https://jira.example.com/secure/attachment/10000/small.txt",
        }
        mock_meta_resp = _mock_response(200, metadata)
        mock_download_resp = MagicMock(spec=httpx.Response)
        mock_download_resp.status_code = 200
        mock_download_resp.content = b"hello"
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.return_value = mock_download_resp
                result = client.download_attachment("10000", max_size=1024)
        assert result["size"] == 5

    def test_download_error_response(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10000",
            "filename": "test.txt",
            "mimeType": "text/plain",
            "size": 5,
            "content": "https://jira.example.com/secure/attachment/10000/test.txt",
        }
        mock_meta_resp = _mock_response(200, metadata)
        mock_download_resp = _mock_response(403)
        mock_download_resp.request.url = "https://jira.example.com/secure/attachment/10000/test.txt"
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.return_value = mock_download_resp
                with pytest.raises(ValueError, match="Permission denied"):
                    client.download_attachment("10000")

    def test_download_timeout(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10000",
            "filename": "test.txt",
            "mimeType": "text/plain",
            "size": 5,
            "content": "https://jira.example.com/secure/attachment/10000/test.txt",
        }
        mock_meta_resp = _mock_response(200, metadata)
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.side_effect = httpx.TimeoutException("timeout")
                with pytest.raises(ValueError, match="Timeout downloading attachment"):
                    client.download_attachment("10000")

    def test_download_string_size_in_metadata(self) -> None:
        client = JiraClient(_make_config())
        metadata = {
            "id": "10000",
            "filename": "test.txt",
            "mimeType": "text/plain",
            "size": "5",
            "content": "https://jira.example.com/secure/attachment/10000/test.txt",
        }
        mock_meta_resp = _mock_response(200, metadata)
        mock_download_resp = MagicMock(spec=httpx.Response)
        mock_download_resp.status_code = 200
        mock_download_resp.content = b"hello"
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.return_value = mock_download_resp
                result = client.download_attachment("10000")
        assert result["size"] == 5


class TestWorklogOperations:
    def test_add_worklog_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(201, {"id": "10000", "timeSpent": "2h"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.add_worklog("TEST-1", "2h")
        assert result["id"] == "10000"

    def test_add_worklog_200(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"id": "10000"})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.add_worklog("TEST-1", "2h")
        assert result["id"] == "10000"

    def test_add_worklog_with_comment_and_started(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(201, {"id": "10000", "timeSpent": "1h"})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            result = client.add_worklog("TEST-1", "1h", comment="Working on it", started="2024-01-01T00:00:00.000+0000")
        call_data = mock_req.call_args[1]["json"]
        assert call_data["timeSpent"] == "1h"
        assert call_data["comment"] == "Working on it"
        assert call_data["started"] == "2024-01-01T00:00:00.000+0000"
        assert result["id"] == "10000"

    def test_add_worklog_without_optional_fields(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(201, {"id": "10000"})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.add_worklog("TEST-1", "30m")
        call_data = mock_req.call_args[1]["json"]
        assert call_data == {"timeSpent": "30m"}

    def test_add_worklog_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/worklog"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.add_worklog("TEST-1", "2h")

    def test_add_worklog_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout adding worklog"):
                client.add_worklog("TEST-1", "2h")

    def test_list_worklogs_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"worklogs": [{"id": "1", "timeSpent": "2h"}], "total": 1})
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.list_worklogs("TEST-1")
        assert result["total"] == 1
        assert len(result["worklogs"]) == 1

    def test_list_worklogs_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/worklog"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_worklogs("TEST-1")

    def test_list_worklogs_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout listing worklogs"):
                client.list_worklogs("TEST-1")

    def test_delete_worklog_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(204)
        with patch.object(client, "_request", return_value=mock_resp):
            client.delete_worklog("TEST-1", "10000")

    def test_delete_worklog_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(404)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/worklog/10000"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.delete_worklog("TEST-1", "10000")

    def test_delete_worklog_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout deleting worklog"):
                client.delete_worklog("TEST-1", "10000")

    def test_delete_worklog_permission_denied(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(403)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1/worklog/10000"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.delete_worklog("TEST-1", "10000")


class TestPriorityAndStatus:
    def test_list_priorities_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, [{"id": "1", "name": "High"}])
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.list_priorities()
        assert result[0]["name"] == "High"

    def test_list_priorities_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/priority"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_priorities()

    def test_list_priorities_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout listing priorities"):
                client.list_priorities()

    def test_list_statuses_success(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, [{"id": "1", "name": "Open"}])
        with patch.object(client, "_request", return_value=mock_resp):
            result = client.list_statuses()
        assert result[0]["name"] == "Open"

    def test_list_statuses_error(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(401)
        mock_resp.request.url = "https://jira.example.com/rest/api/2/status"
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_statuses()

    def test_list_statuses_timeout(self) -> None:
        client = JiraClient(_make_config())
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Timeout listing statuses"):
                client.list_statuses()


class TestRequestMethod:
    def test_request_makes_http_call(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"ok": True})
        with patch("httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.request.return_value = mock_resp
            resp = client._request("GET", "https://jira.example.com/rest/api/2/test")
        assert resp.status_code == 200
        mock_ctx.request.assert_called_once()


class TestHandleError:
    def test_400_with_errors_dict(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(400, {"errors": {"summary": "Field is required"}, "errorMessages": []})
        resp.request.content = b'{"fields": {"summary": "test"}}'
        with pytest.raises(ValueError, match="Validation error: summary: Field is required"):
            client._handle_error(resp)

    def test_400_disallowed_chars_with_non_ascii(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(
            400,
            {"errors": {"description": "contains disallowed characters"}, "errorMessages": []},
        )
        resp.request.content = "hello \u200b world".encode("utf-8")
        with pytest.raises(ValueError, match="Hint: Non-ASCII characters in request body: U\\+200B"):
            client._handle_error(resp)

    def test_400_disallowed_chars_no_non_ascii(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(
            400,
            {"errors": {"description": "contains disallowed characters"}, "errorMessages": []},
        )
        resp.request.content = b"plain ascii text"
        with pytest.raises(ValueError, match="Hint: No obvious non-ASCII characters"):
            client._handle_error(resp)

    def test_400_non_disallowed_error_no_hint(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(400, {"errors": {"summary": "Field is required"}, "errorMessages": []})
        resp.request.content = b'{"fields": {"summary": ""}}'
        with pytest.raises(ValueError, match="^Validation error: summary: Field is required$"):
            client._handle_error(resp)

    def test_400_disallowed_chars_decode_error(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(
            400,
            {"errors": {"description": "contains disallowed characters"}, "errorMessages": []},
        )
        resp.request.content = MagicMock()
        resp.request.content.decode = MagicMock(side_effect=Exception("decode failed"))
        with pytest.raises(ValueError, match="Validation error"):
            client._handle_error(resp)

    def test_400_disallowed_chars_max_10_suspicious(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(
            400,
            {"errors": {"description": "contains disallowed characters"}, "errorMessages": []},
        )
        many_non_ascii = "".join(chr(0x0100 + i) for i in range(20))
        resp.request.content = many_non_ascii.encode("utf-8")
        with pytest.raises(ValueError, match="Hint: Non-ASCII characters"):
            client._handle_error(resp)
        try:
            client._handle_error(resp)
        except ValueError as e:
            chars = str(e).split("Non-ASCII characters in request body: ")[1].split(", ")
            assert len(chars) == 10

    def test_400_with_error_messages(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(400, {"errors": {}, "errorMessages": ["Something went wrong"]})
        with pytest.raises(ValueError, match="Validation error: Something went wrong"):
            client._handle_error(resp)

    def test_400_with_unparseable_json(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(400, text="not json")
        resp.json.side_effect = ValueError("bad json")
        with pytest.raises(ValueError, match="Bad request: not json"):
            client._handle_error(resp)

    def test_400_with_key_error(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(400, text="bad request body")
        resp.json.side_effect = KeyError("missing key")
        with pytest.raises(ValueError, match="Bad request: bad request body"):
            client._handle_error(resp)

    def test_401(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(401)
        with pytest.raises(ValueError, match="Authentication failed"):
            client._handle_error(resp)

    def test_403(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(403)
        with pytest.raises(ValueError, match="Permission denied"):
            client._handle_error(resp)

    def test_404_issue(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(404)
        resp.request.url = "https://jira.example.com/rest/api/2/issue/TEST-1"
        with pytest.raises(ValueError, match="Resource not found.*issue"):
            client._handle_error(resp)

    def test_404_project(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(404)
        resp.request.url = "https://jira.example.com/rest/api/2/project/PROJ"
        with pytest.raises(ValueError, match="Resource not found.*project"):
            client._handle_error(resp)

    def test_404_filter(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(404)
        resp.request.url = "https://jira.example.com/rest/api/2/filter/100"
        with pytest.raises(ValueError, match="Resource not found.*filter"):
            client._handle_error(resp)

    def test_404_board(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(404)
        resp.request.url = "https://jira.example.com/rest/agile/1.0/board/1"
        with pytest.raises(ValueError, match="Resource not found.*board"):
            client._handle_error(resp)

    def test_404_sprint(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(404)
        resp.request.url = "https://jira.example.com/rest/agile/1.0/sprint/1"
        with pytest.raises(ValueError, match="Resource not found.*sprint"):
            client._handle_error(resp)

    def test_404_user(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(404)
        resp.request.url = "https://jira.example.com/rest/api/2/user?username=x"
        with pytest.raises(ValueError, match="Resource not found.*user"):
            client._handle_error(resp)

    def test_404_generic(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(404)
        resp.request.url = "https://jira.example.com/rest/api/2/something"
        with pytest.raises(ValueError, match="Resource not found.*resource"):
            client._handle_error(resp)

    def test_429(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(429)
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            client._handle_error(resp)

    def test_500(self) -> None:
        client = JiraClient(_make_config())
        resp = _mock_response(500, text="Internal error")
        with pytest.raises(ValueError, match="Jira API error \\(500\\)"):
            client._handle_error(resp)


class TestFieldsParameter:
    def test_get_issue_with_fields(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"key": "TEST-1", "fields": {}})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.get_issue("TEST-1", fields="summary,status")
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["params"]["fields"] == "summary,status"

    def test_get_issue_without_fields(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"key": "TEST-1", "fields": {}})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.get_issue("TEST-1")
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["params"] == {}

    def test_search_issues_with_fields(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"issues": [], "total": 0})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.search_issues("project = TEST", fields="summary,status")
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["json"]["fields"] == ["summary", "status"]

    def test_get_sprint_issues_with_fields(self) -> None:
        client = JiraClient(_make_config())
        mock_resp = _mock_response(200, {"issues": [], "total": 0})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.get_sprint_issues("42", fields="summary,status")
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["params"]["fields"] == "summary,status"
