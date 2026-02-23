"""Tests for ConfluenceClient."""

import base64
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import httpx
import pytest

from confluence_mcp_server.client import ConfluenceClient
from confluence_mcp_server.config import AuthType, ConfluenceConfig


def _make_config(
    url: str = "https://confluence.example.com",
    token: str = "test-token",
    email: str | None = None,
    auth_type: AuthType | None = None,
    timeout: int = 30,
    verify_ssl: bool = True,
) -> ConfluenceConfig:
    config = MagicMock(spec=ConfluenceConfig)
    config.url = url
    config.token = token
    config.email = email
    config.auth_type = auth_type
    config.timeout = timeout
    config.verify_ssl = verify_ssl
    return config


def _mock_response(
    status_code: int = 200,
    json_data: Dict[str, Any] | None = None,
    text: str = "",
) -> httpx.Response:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    return response


class TestAuthHeaders:
    def test_bearer_auth_for_pat(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_basic_auth_for_cloud(self) -> None:
        config = _make_config(
            url="https://company.atlassian.net",
            email="user@company.com",
            auth_type=AuthType.CLOUD,
        )
        client = ConfluenceClient(config)
        headers = client._get_headers()
        expected = base64.b64encode(b"user@company.com:test-token").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_no_auth_type_defaults_to_pat(self) -> None:
        config = _make_config(auth_type=None)
        client = ConfluenceClient(config)
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-token"


class TestAPIBase:
    def test_cloud_api_base(self) -> None:
        config = _make_config(
            url="https://company.atlassian.net",
            auth_type=AuthType.CLOUD,
        )
        client = ConfluenceClient(config)
        assert client._api_base == "https://company.atlassian.net/wiki/rest/api"

    def test_dc_api_base(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        assert client._api_base == "https://confluence.example.com/rest/api"


class TestHealthCheck:
    def test_successful_health_check(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"some": "data"})
        with patch.object(client, "_request", return_value=resp):
            result = client.health_check()
        assert result["connected"] is True
        assert result["base_url"] == "https://confluence.example.com"
        assert result["auth_type"] == "pat"

    def test_health_check_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.health_check()

    def test_health_check_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Connection timeout"):
                client.health_check()

    def test_health_check_network_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.NetworkError("fail")):
            with pytest.raises(ValueError, match="Network error"):
                client.health_check()


class TestGetPage:
    def test_get_page_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        page_data = {"id": "123", "title": "Test Page"}
        resp = _mock_response(200, page_data)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.get_page("123")
        assert result == page_data
        call_args = mock_req.call_args
        assert call_args[0][0] == "GET"
        assert "content/123" in call_args[0][1]

    def test_get_page_custom_expand(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"id": "123"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            client.get_page("123", expand="version")
        assert mock_req.call_args[1]["params"]["expand"] == "version"

    def test_get_page_not_found(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_page("999")

    def test_get_page_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting page"):
                client.get_page("123")


class TestGetPageByTitle:
    def test_found(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        page = {"id": "1", "title": "Found"}
        resp = _mock_response(200, {"results": [page]})
        with patch.object(client, "_request", return_value=resp):
            result = client.get_page_by_title("DEV", "Found")
        assert result == page

    def test_not_found(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"results": []})
        with patch.object(client, "_request", return_value=resp):
            result = client.get_page_by_title("DEV", "Missing")
        assert result is None

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout searching page"):
                client.get_page_by_title("DEV", "Test")

    def test_error_response(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.get_page_by_title("DEV", "Test")


class TestCreatePage:
    def test_create_without_parent(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        created = {"id": "10", "title": "New Page"}
        resp = _mock_response(201, created)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.create_page("DEV", "New Page", "<p>content</p>")
        assert result == created
        payload = mock_req.call_args[1]["json"]
        assert payload["type"] == "page"
        assert payload["title"] == "New Page"
        assert payload["space"]["key"] == "DEV"
        assert "ancestors" not in payload

    def test_create_with_parent(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"id": "11"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            client.create_page("DEV", "Child", "<p>child</p>", parent_id="5")
        payload = mock_req.call_args[1]["json"]
        assert payload["ancestors"] == [{"id": "5"}]

    def test_create_page_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating page"):
                client.create_page("DEV", "New", "<p>x</p>")

    def test_create_page_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(400, text="bad input")
        resp.json.side_effect = ValueError("no json")
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Bad request"):
                client.create_page("DEV", "Bad", "<p>x</p>")


class TestUpdatePage:
    def test_update_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"id": "1", "version": {"number": 3}})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.update_page("1", "Updated", "<p>new</p>", 2)
        payload = mock_req.call_args[1]["json"]
        assert payload["version"]["number"] == 3
        assert payload["title"] == "Updated"
        assert result["id"] == "1"

    def test_update_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout updating page"):
                client.update_page("1", "T", "<p>x</p>", 1)

    def test_update_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.update_page("1", "T", "<p>x</p>", 1)


class TestDeletePage:
    def test_delete_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(204)
        with patch.object(client, "_request", return_value=resp):
            client.delete_page("1")

    def test_delete_not_found(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.delete_page("999")

    def test_delete_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting page"):
                client.delete_page("1")


class TestMovePage:
    def test_move_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"id": "1"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.move_page("1", "2", "before")
        assert "move/before/2" in mock_req.call_args[0][1]
        assert result == {"id": "1"}

    def test_move_default_position(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"id": "1"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            client.move_page("1", "2")
        assert "move/append/2" in mock_req.call_args[0][1]

    def test_move_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout moving page"):
                client.move_page("1", "2")

    def test_move_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.move_page("1", "2")


class TestCopyPage:
    def test_copy_without_title(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(201, {"id": "10"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.copy_page("1", "DEST")
        payload = mock_req.call_args[1]["json"]
        assert "pageTitle" not in payload
        assert payload["destination"]["value"] == "DEST"
        assert result == {"id": "10"}

    def test_copy_with_title(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"id": "10"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            client.copy_page("1", "DEST", title="Copy Title")
        payload = mock_req.call_args[1]["json"]
        assert payload["pageTitle"] == "Copy Title"

    def test_copy_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout copying page"):
                client.copy_page("1", "DEST")

    def test_copy_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.copy_page("1", "DEST")


class TestGetChildren:
    def test_get_children_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        children_data = {"results": [{"id": "2"}, {"id": "3"}]}
        resp = _mock_response(200, children_data)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.get_children("1", limit=10, start=5)
        assert result == children_data
        params = mock_req.call_args[1]["params"]
        assert params["limit"] == 10
        assert params["start"] == 5

    def test_get_children_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting children"):
                client.get_children("1")

    def test_get_children_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.get_children("1")


class TestGetAncestors:
    def test_get_ancestors_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        ancestors = [{"id": "parent"}, {"id": "grandparent"}]
        with patch.object(client, "get_page", return_value={"ancestors": ancestors}):
            result = client.get_ancestors("1")
        assert result == ancestors

    def test_get_ancestors_empty(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "get_page", return_value={}):
            result = client.get_ancestors("1")
        assert result == []


class TestGetHistory:
    def test_get_history_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        history_data = {"latest": True}
        resp = _mock_response(200, history_data)
        with patch.object(client, "_request", return_value=resp):
            result = client.get_history("1")
        assert result == history_data

    def test_get_history_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting history"):
                client.get_history("1")

    def test_get_history_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.get_history("1")


class TestGetPageVersion:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        version_data = {"number": 3}
        resp = _mock_response(200, version_data)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.get_page_version("1", 3)
        assert "version/3" in mock_req.call_args[0][1]
        assert result == version_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting version"):
                client.get_page_version("1", 3)

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_page_version("1", 3)


class TestRestorePageVersion:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"restored": True})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.restore_page_version("1", 2, "rollback")
        payload = mock_req.call_args[1]["json"]
        assert payload["operationKey"] == "restore"
        assert payload["params"]["versionNumber"] == 2
        assert payload["params"]["message"] == "rollback"
        assert result == {"restored": True}

    def test_status_201(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(201, {"restored": True})
        with patch.object(client, "_request", return_value=resp):
            result = client.restore_page_version("1", 2)
        assert result == {"restored": True}

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout restoring version"):
                client.restore_page_version("1", 2)

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.restore_page_version("1", 2)


class TestSearchCQL:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        search_data = {"results": [{"id": "1"}]}
        resp = _mock_response(200, search_data)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.search_cql("type=page", limit=10, start=5)
        params = mock_req.call_args[1]["params"]
        assert params["cql"] == "type=page"
        assert params["limit"] == 10
        assert params["start"] == 5
        assert result == search_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout executing CQL"):
                client.search_cql("type=page")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.search_cql("type=page")


class TestSearchContent:
    def test_basic_search(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "search_cql", return_value={"results": []}) as mock_cql:
            client.search_content("hello")
        cql = mock_cql.call_args[1]["cql"]
        assert 'text ~ "hello"' in cql

    def test_search_with_space_key(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "search_cql", return_value={"results": []}) as mock_cql:
            client.search_content("hello", space_key="DEV")
        cql = mock_cql.call_args[1]["cql"]
        assert 'space = "DEV"' in cql

    def test_search_with_content_type(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "search_cql", return_value={"results": []}) as mock_cql:
            client.search_content("hello", content_type="page")
        cql = mock_cql.call_args[1]["cql"]
        assert 'type = "page"' in cql

    def test_search_all_filters(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "search_cql", return_value={"results": []}) as mock_cql:
            client.search_content("hello", space_key="DEV", content_type="blogpost", limit=10, start=5)
        cql = mock_cql.call_args[1]["cql"]
        assert 'text ~ "hello"' in cql
        assert 'space = "DEV"' in cql
        assert 'type = "blogpost"' in cql
        assert mock_cql.call_args[1]["limit"] == 10
        assert mock_cql.call_args[1]["start"] == 5


class TestListSpaces:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        spaces_data = {"results": [{"key": "DEV"}]}
        resp = _mock_response(200, spaces_data)
        with patch.object(client, "_request", return_value=resp):
            result = client.list_spaces()
        assert result == spaces_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing spaces"):
                client.list_spaces()

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_spaces()


class TestGetSpace:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"key": "DEV"})
        with patch.object(client, "_request", return_value=resp):
            result = client.get_space("DEV")
        assert result == {"key": "DEV"}

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting space"):
                client.get_space("DEV")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_space("MISSING")


class TestCreateSpace:
    def test_create_with_description(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(201, {"key": "NEW"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.create_space("NEW", "New Space", "A description")
        payload = mock_req.call_args[1]["json"]
        assert payload["key"] == "NEW"
        assert payload["name"] == "New Space"
        assert payload["description"]["plain"]["value"] == "A description"
        assert result == {"key": "NEW"}

    def test_create_without_description(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"key": "NEW"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            client.create_space("NEW", "New Space")
        payload = mock_req.call_args[1]["json"]
        assert "description" not in payload

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating space"):
                client.create_space("NEW", "New")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.create_space("NEW", "New")


class TestAddComment:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(201, {"id": "c1"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.add_comment("1", "<p>nice</p>")
        payload = mock_req.call_args[1]["json"]
        assert payload["type"] == "comment"
        assert payload["container"]["id"] == "1"
        assert result == {"id": "c1"}

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout adding comment"):
                client.add_comment("1", "text")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.add_comment("1", "text")


class TestListComments:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        comments_data = {"results": [{"id": "c1"}]}
        resp = _mock_response(200, comments_data)
        with patch.object(client, "_request", return_value=resp):
            result = client.list_comments("1")
        assert result == comments_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing comments"):
                client.list_comments("1")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.list_comments("1")


class TestUpdateComment:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"id": "c1"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.update_comment("c1", "<p>updated</p>", 1)
        payload = mock_req.call_args[1]["json"]
        assert payload["version"]["number"] == 2
        assert result == {"id": "c1"}

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout updating comment"):
                client.update_comment("c1", "text", 1)

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.update_comment("c1", "text", 1)


class TestDeleteComment:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(204)
        with patch.object(client, "_request", return_value=resp):
            client.delete_comment("c1")

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting comment"):
                client.delete_comment("c1")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.delete_comment("c1")


class TestAddAttachment:
    def test_success(self, tmp_path: Path) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        f = tmp_path / "file.txt"
        f.write_bytes(b"content")
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "att1"}

        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_http_client):
            result = client.add_attachment("1", str(f))
        assert result == {"id": "att1"}

    def test_custom_filename(self, tmp_path: Path) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        f = tmp_path / "file.txt"
        f.write_bytes(b"content")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "att1"}

        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_http_client):
            result = client.add_attachment("1", str(f), filename="custom.txt")
        assert result == {"id": "att1"}
        call_kwargs = mock_http_client.post.call_args[1]
        file_tuple = call_kwargs["files"]["file"]
        assert file_tuple[0] == "custom.txt"

    def test_timeout(self, tmp_path: Path) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        f = tmp_path / "file.txt"
        f.write_bytes(b"content")
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.post.side_effect = httpx.TimeoutException("timeout")

        with patch("httpx.Client", return_value=mock_http_client):
            with pytest.raises(ValueError, match="Timeout adding attachment"):
                client.add_attachment("1", str(f))

    def test_file_not_found(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with pytest.raises(ValueError, match="File not found"):
            client.add_attachment("1", "/nonexistent/file.txt")

    def test_error_response(self, tmp_path: Path) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        f = tmp_path / "file.txt"
        f.write_bytes(b"content")
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_http_client):
            with pytest.raises(ValueError, match="Permission denied"):
                client.add_attachment("1", str(f))


class TestListAttachments:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        data = {"results": [{"id": "att1"}]}
        resp = _mock_response(200, data)
        with patch.object(client, "_request", return_value=resp):
            result = client.list_attachments("1")
        assert result == data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing attachments"):
                client.list_attachments("1")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.list_attachments("1")


class TestGetAttachment:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        data = {"id": "att1", "title": "file.txt"}
        resp = _mock_response(200, data)
        with patch.object(client, "_request", return_value=resp):
            result = client.get_attachment("att1")
        assert result == data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting attachment"):
                client.get_attachment("att1")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_attachment("att1")


class TestDeleteAttachment:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(204)
        with patch.object(client, "_request", return_value=resp):
            client.delete_attachment("att1")

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting attachment"):
                client.delete_attachment("att1")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.delete_attachment("att1")


class TestDownloadAttachment:
    def test_download_text_file(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att1",
            "title": "readme.txt",
            "extensions": {"mediaType": "text/plain", "fileSize": 13},
            "_links": {"download": "/download/attachments/123/readme.txt"},
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
                result = client.download_attachment("att1")
        assert result["content"] == "Hello, World!"
        assert result["encoding"] == "text"
        assert result["filename"] == "readme.txt"
        assert result["size"] == 13
        assert result["mime_type"] == "text/plain"

    def test_download_binary_file(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att2",
            "title": "image.png",
            "extensions": {"mediaType": "image/png", "fileSize": 4},
            "_links": {"download": "/download/attachments/123/image.png"},
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
                result = client.download_attachment("att2")
        assert result["content"] == base64.b64encode(b"\x89PNG").decode("ascii")
        assert result["encoding"] == "base64"
        assert result["mime_type"] == "image/png"

    def test_download_json_is_text(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att3",
            "title": "data.json",
            "extensions": {"mediaType": "application/json", "fileSize": 2},
            "_links": {"download": "/download/attachments/123/data.json"},
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
                result = client.download_attachment("att3")
        assert result["encoding"] == "text"

    def test_download_no_download_link(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {"id": "att1", "title": "test.txt", "extensions": {}, "_links": {}}
        mock_meta_resp = _mock_response(200, metadata)
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with pytest.raises(ValueError, match="No download URL found"):
                client.download_attachment("att1")

    def test_download_size_exceeds_limit_from_metadata(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att1",
            "title": "huge.bin",
            "extensions": {"mediaType": "application/octet-stream", "fileSize": 20_000_000},
            "_links": {"download": "/download/attachments/123/huge.bin"},
        }
        mock_meta_resp = _mock_response(200, metadata)
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with pytest.raises(ValueError, match="exceeds.*byte limit"):
                client.download_attachment("att1")

    def test_download_size_exceeds_limit_from_actual(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att1",
            "title": "sneaky.bin",
            "extensions": {"mediaType": "application/octet-stream", "fileSize": 100},
            "_links": {"download": "/download/attachments/123/sneaky.bin"},
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
                    client.download_attachment("att1", max_size=150)

    def test_download_error_response(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att1",
            "title": "test.txt",
            "extensions": {"mediaType": "text/plain", "fileSize": 5},
            "_links": {"download": "/download/attachments/123/test.txt"},
        }
        mock_meta_resp = _mock_response(200, metadata)
        mock_download_resp = _mock_response(403)
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.return_value = mock_download_resp
                with pytest.raises(ValueError, match="Permission denied"):
                    client.download_attachment("att1")

    def test_download_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att1",
            "title": "test.txt",
            "extensions": {"mediaType": "text/plain", "fileSize": 5},
            "_links": {"download": "/download/attachments/123/test.txt"},
        }
        mock_meta_resp = _mock_response(200, metadata)
        with patch.object(client, "_request", return_value=mock_meta_resp):
            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.get.side_effect = httpx.TimeoutException("timeout")
                with pytest.raises(ValueError, match="Timeout downloading attachment"):
                    client.download_attachment("att1")

    def test_download_string_size_in_metadata(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att1",
            "title": "test.txt",
            "extensions": {"mediaType": "text/plain", "fileSize": "5"},
            "_links": {"download": "/download/attachments/123/test.txt"},
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
                result = client.download_attachment("att1")
        assert result["size"] == 5

    def test_download_constructs_correct_url(self) -> None:
        config = _make_config(url="https://confluence.example.com", auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        metadata = {
            "id": "att1",
            "title": "test.txt",
            "extensions": {"mediaType": "text/plain", "fileSize": 5},
            "_links": {"download": "/download/attachments/123/test.txt"},
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
                client.download_attachment("att1")
        call_args = mock_ctx.get.call_args
        assert call_args[0][0] == "https://confluence.example.com/download/attachments/123/test.txt"


class TestAddLabel:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"results": [{"name": "important"}]})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.add_label("1", "important")
        payload = mock_req.call_args[1]["json"]
        assert payload == [{"prefix": "global", "name": "important"}]
        assert result["results"][0]["name"] == "important"

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout adding label"):
                client.add_label("1", "test")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.add_label("1", "test")


class TestRemoveLabel:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(204)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            client.remove_label("1", "old-label")
        assert "label/old-label" in mock_req.call_args[0][1]

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout removing label"):
                client.remove_label("1", "test")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.remove_label("1", "test")


class TestGetLabels:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        labels_data = {"results": [{"name": "a"}, {"name": "b"}]}
        resp = _mock_response(200, labels_data)
        with patch.object(client, "_request", return_value=resp):
            result = client.get_labels("1")
        assert result == labels_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting labels"):
                client.get_labels("1")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.get_labels("1")


class TestConvertContent:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        converted = {"value": "<p>text</p>", "representation": "storage"}
        resp = _mock_response(200, converted)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.convert_content("<p>text</p>", "wiki", "storage")
        assert "convert/storage" in mock_req.call_args[0][1]
        payload = mock_req.call_args[1]["json"]
        assert payload["value"] == "<p>text</p>"
        assert payload["representation"] == "wiki"
        assert result == converted

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout converting content"):
                client.convert_content("text", "wiki", "storage")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(400, text="bad conversion")
        resp.json.side_effect = ValueError("no json")
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Bad request"):
                client.convert_content("text", "wiki", "storage")


class TestGetUser:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        user_data = {"accountId": "abc123", "displayName": "Test User"}
        resp = _mock_response(200, user_data)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.get_user("abc123")
        params = mock_req.call_args[1]["params"]
        assert params["accountId"] == "abc123"
        assert result == user_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting user"):
                client.get_user("abc123")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.get_user("abc123")


class TestGetCurrentUser:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        user_data = {"displayName": "Current User"}
        resp = _mock_response(200, user_data)
        with patch.object(client, "_request", return_value=resp):
            result = client.get_current_user()
        assert result == user_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting current user"):
                client.get_current_user()

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.get_current_user()


class TestCreateBlog:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        blog_data = {"id": "b1", "type": "blogpost"}
        resp = _mock_response(201, blog_data)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.create_blog("DEV", "My Blog", "<p>blog content</p>")
        payload = mock_req.call_args[1]["json"]
        assert payload["type"] == "blogpost"
        assert payload["title"] == "My Blog"
        assert payload["space"]["key"] == "DEV"
        assert result == blog_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating blog"):
                client.create_blog("DEV", "Blog", "<p>x</p>")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.create_blog("DEV", "Blog", "<p>x</p>")


class TestListBlogs:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        blogs_data = {"results": [{"id": "b1"}]}
        resp = _mock_response(200, blogs_data)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.list_blogs("DEV", limit=10, start=5)
        params = mock_req.call_args[1]["params"]
        assert params["type"] == "blogpost"
        assert params["spaceKey"] == "DEV"
        assert result == blogs_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing blog"):
                client.list_blogs("DEV")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(429)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                client.list_blogs("DEV")


class TestListSpacePages:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        pages_data = {"results": [{"id": "p1", "title": "Page One"}], "size": 1}
        resp = _mock_response(200, pages_data)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.list_space_pages("DEV", limit=10, start=5)
        params = mock_req.call_args[1]["params"]
        assert params["type"] == "page"
        assert params["spaceKey"] == "DEV"
        assert params["limit"] == 10
        assert params["start"] == 5
        assert result == pages_data

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing pages in space DEV"):
                client.list_space_pages("DEV")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(429)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                client.list_space_pages("DEV")


class TestGetBlog:
    def test_delegates_to_get_page(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        page_data = {"id": "b1", "type": "blogpost"}
        with patch.object(client, "get_page", return_value=page_data) as mock_get:
            result = client.get_blog("b1")
        mock_get.assert_called_once_with("b1")
        assert result == page_data


class TestUpdateBlog:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(200, {"id": "b1"})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.update_blog("b1", "Updated Blog", "<p>new</p>", 2)
        payload = mock_req.call_args[1]["json"]
        assert payload["type"] == "blogpost"
        assert payload["version"]["number"] == 3
        assert result == {"id": "b1"}

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout updating blog"):
                client.update_blog("b1", "T", "<p>x</p>", 1)

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.update_blog("b1", "T", "<p>x</p>", 1)


class TestDeleteBlog:
    def test_delete_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(204)
        with patch.object(client, "_request", return_value=resp):
            client.delete_blog("b1")

    def test_delete_not_found(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Resource not found"):
                client.delete_blog("b999")

    def test_delete_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting blog"):
                client.delete_blog("b1")


class TestGetPagePermissions:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        perms = {"results": []}
        resp = _mock_response(200, perms)
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.get_page_permissions("1")
        assert "restriction" in mock_req.call_args[0][1]
        assert result == perms

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting permissions"):
                client.get_page_permissions("1")

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Permission denied"):
                client.get_page_permissions("1")


class TestSetPagePermissions:
    def test_success(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        restrictions = [{"operation": "read", "restrictions": {"user": []}}]
        resp = _mock_response(200, {"results": restrictions})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.set_page_permissions("1", restrictions)
        assert mock_req.call_args[1]["json"] == restrictions
        assert result["results"] == restrictions

    def test_timeout(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        with patch.object(client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout setting permissions"):
                client.set_page_permissions("1", [])

    def test_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with patch.object(client, "_request", return_value=resp):
            with pytest.raises(ValueError, match="Authentication failed"):
                client.set_page_permissions("1", [])


class TestHandleError:
    def test_401(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(401)
        with pytest.raises(ValueError, match="Authentication failed"):
            client._handle_error(resp)

    def test_403(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(403)
        with pytest.raises(ValueError, match="Permission denied"):
            client._handle_error(resp)

    def test_404(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(404)
        with pytest.raises(ValueError, match="Resource not found"):
            client._handle_error(resp)

    def test_429(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(429)
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            client._handle_error(resp)

    def test_400_with_json_message(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(400, json_data={"message": "Invalid field"})
        with pytest.raises(ValueError, match="Validation error: Invalid field"):
            client._handle_error(resp)

    def test_400_with_empty_message(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(400, json_data={"message": ""}, text="raw error text")
        with pytest.raises(ValueError, match="Bad request: raw error text"):
            client._handle_error(resp)

    def test_400_with_no_json(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(400, text="not json")
        resp.json.side_effect = ValueError("no json")
        with pytest.raises(ValueError, match="Bad request: not json"):
            client._handle_error(resp)

    def test_generic_error(self) -> None:
        config = _make_config(auth_type=AuthType.PAT)
        client = ConfluenceClient(config)
        resp = _mock_response(500, text="Internal Server Error")
        with pytest.raises(ValueError, match="Confluence API error \\(500\\)"):
            client._handle_error(resp)


class TestRenderMacro:
    def _make_client(self) -> ConfluenceClient:
        config = _make_config(auth_type=AuthType.PAT)
        return ConfluenceClient(config)

    def test_simple_macro_no_params_no_body(self) -> None:
        client = self._make_client()
        result = client.render_macro("toc")
        assert result["macro_name"] == "toc"
        assert result["xhtml"] == '<ac:structured-macro ac:name="toc"></ac:structured-macro>'

    def test_macro_with_parameters(self) -> None:
        client = self._make_client()
        result = client.render_macro("toc", parameters={"maxLevel": "3", "printable": "false"})
        xhtml = result["xhtml"]
        assert '<ac:parameter ac:name="maxLevel">3</ac:parameter>' in xhtml
        assert '<ac:parameter ac:name="printable">false</ac:parameter>' in xhtml
        assert xhtml.startswith('<ac:structured-macro ac:name="toc">')
        assert xhtml.endswith("</ac:structured-macro>")

    def test_macro_with_plain_text_body(self) -> None:
        client = self._make_client()
        result = client.render_macro("code", body="print('hello')", body_type="plain-text-body")
        xhtml = result["xhtml"]
        assert "<ac:plain-text-body><![CDATA[print('hello')]]></ac:plain-text-body>" in xhtml

    def test_macro_with_rich_text_body(self) -> None:
        client = self._make_client()
        result = client.render_macro("panel", body="<p>Panel content</p>")
        xhtml = result["xhtml"]
        assert "<ac:rich-text-body>&lt;p&gt;Panel content&lt;/p&gt;</ac:rich-text-body>" in xhtml

    def test_macro_with_params_and_body(self) -> None:
        client = self._make_client()
        result = client.render_macro(
            "code",
            parameters={"language": "python", "title": "Example"},
            body="x = 1",
            body_type="plain-text-body",
        )
        xhtml = result["xhtml"]
        assert '<ac:parameter ac:name="language">python</ac:parameter>' in xhtml
        assert '<ac:parameter ac:name="title">Example</ac:parameter>' in xhtml
        assert "<ac:plain-text-body><![CDATA[x = 1]]></ac:plain-text-body>" in xhtml

    def test_cdata_escaping(self) -> None:
        client = self._make_client()
        result = client.render_macro("code", body="if (a]]>b) { }", body_type="plain-text-body")
        xhtml = result["xhtml"]
        assert "<ac:plain-text-body><![CDATA[if (a]]]]><![CDATA[>b) { }]]></ac:plain-text-body>" in xhtml

    def test_xml_escape_in_parameter_values(self) -> None:
        client = self._make_client()
        result = client.render_macro("info", parameters={"title": "A & B <C>"})
        xhtml = result["xhtml"]
        assert "A &amp; B &lt;C&gt;" in xhtml

    def test_xml_escape_in_parameter_keys(self) -> None:
        client = self._make_client()
        result = client.render_macro("test", parameters={"key&name": "value"})
        xhtml = result["xhtml"]
        assert 'ac:name="key&amp;name"' in xhtml

    def test_empty_macro_name_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="macro_name must not be empty"):
            client.render_macro("")

    def test_whitespace_only_macro_name_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="macro_name must not be empty"):
            client.render_macro("   ")

    def test_invalid_macro_name_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="Invalid macro_name"):
            client.render_macro("bad macro!")

    def test_macro_name_starting_with_digit_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="Invalid macro_name"):
            client.render_macro("123macro")

    def test_invalid_body_type_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="Invalid body_type"):
            client.render_macro("code", body="x", body_type="unknown")

    def test_custom_plugin_macro_name(self) -> None:
        client = self._make_client()
        result = client.render_macro("my-custom-plugin")
        assert result["macro_name"] == "my-custom-plugin"
        assert 'ac:name="my-custom-plugin"' in result["xhtml"]

    def test_macro_name_with_underscore(self) -> None:
        client = self._make_client()
        result = client.render_macro("my_macro")
        assert result["macro_name"] == "my_macro"

    def test_macro_name_stripped(self) -> None:
        client = self._make_client()
        result = client.render_macro("  toc  ")
        assert result["macro_name"] == "toc"
        assert 'ac:name="toc"' in result["xhtml"]

    def test_body_none_omits_body_element(self) -> None:
        client = self._make_client()
        result = client.render_macro("toc", body=None)
        assert "plain-text-body" not in result["xhtml"]
        assert "rich-text-body" not in result["xhtml"]

    def test_empty_parameters_dict(self) -> None:
        client = self._make_client()
        result = client.render_macro("toc", parameters={})
        assert "<ac:parameter" not in result["xhtml"]

    def test_body_with_newlines_preserved(self) -> None:
        client = self._make_client()
        code = "line1\nline2\nline3"
        result = client.render_macro("code", body=code, body_type="plain-text-body")
        assert "line1\nline2\nline3" in result["xhtml"]

    def test_multiple_cdata_escapes(self) -> None:
        client = self._make_client()
        result = client.render_macro("code", body="a]]>b]]>c", body_type="plain-text-body")
        xhtml = result["xhtml"]
        assert "<![CDATA[a]]]]><![CDATA[>b]]]]><![CDATA[>c]]>" in xhtml

    def test_rich_text_body_default(self) -> None:
        client = self._make_client()
        result = client.render_macro("expand", body="<p>content</p>")
        assert "<ac:rich-text-body>&lt;p&gt;content&lt;/p&gt;</ac:rich-text-body>" in result["xhtml"]
        assert "<ac:plain-text-body>" not in result["xhtml"]


class TestRequestMethod:
    def test_request_creates_httpx_client(self) -> None:
        config = _make_config(auth_type=AuthType.PAT, timeout=45, verify_ssl=False)
        client = ConfluenceClient(config)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.request.return_value = mock_response

        with patch("httpx.Client", return_value=mock_http_client) as mock_client_cls:
            result = client._request("GET", "https://example.com/api/test", params={"a": "b"})

        mock_client_cls.assert_called_once_with(timeout=45, verify=False)
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args
        assert call_args[0] == ("GET", "https://example.com/api/test")
        assert "headers" in call_args[1]
        assert call_args[1]["params"] == {"a": "b"}
        assert result == mock_response
