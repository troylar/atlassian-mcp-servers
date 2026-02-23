"""Tests for BitbucketClient."""

import base64
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import httpx
import pytest

from bitbucket_mcp_server.client import BitbucketClient
from bitbucket_mcp_server.config import AuthType, BitbucketConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(
    auth_type: AuthType = AuthType.PAT,
    url: str = "https://bitbucket.example.com",
    token: str = "test-token",
    email: str | None = None,
    workspace: str | None = None,
) -> BitbucketConfig:
    """Build a BitbucketConfig without touching env vars."""
    cfg = MagicMock(spec=BitbucketConfig)
    cfg.url = url
    cfg.token = token
    cfg.email = email
    cfg.auth_type = auth_type
    cfg.workspace = workspace
    cfg.timeout = 30
    cfg.verify_ssl = True
    return cfg


@pytest.fixture()
def dc_client() -> BitbucketClient:
    return BitbucketClient(_make_config(AuthType.PAT))


@pytest.fixture()
def cloud_client() -> BitbucketClient:
    return BitbucketClient(
        _make_config(
            AuthType.CLOUD,
            url="https://bitbucket.org",
            email="user@example.com",
            workspace="myworkspace",
        )
    )


def _mock_response(
    status_code: int = 200,
    json_data: Any = None,
    text: str = "",
    headers: Dict[str, str] | None = None,
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text or ""
    resp.headers = headers or {"content-type": "application/json"}
    return resp


# ---------------------------------------------------------------------------
# Auth headers
# ---------------------------------------------------------------------------

class TestAuthHeaders:
    def test_pat_bearer_header(self, dc_client: BitbucketClient) -> None:
        headers = dc_client._get_headers()
        assert headers["Authorization"] == "Bearer test-token"

    def test_cloud_basic_header(self, cloud_client: BitbucketClient) -> None:
        headers = cloud_client._get_headers()
        expected = base64.b64encode(b"user@example.com:test-token").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_common_headers(self, dc_client: BitbucketClient) -> None:
        headers = dc_client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


# ---------------------------------------------------------------------------
# API base URLs
# ---------------------------------------------------------------------------

class TestAPIBase:
    def test_cloud_api_base(self, cloud_client: BitbucketClient) -> None:
        assert cloud_client._api_base == "https://api.bitbucket.org/2.0"

    def test_dc_api_base(self, dc_client: BitbucketClient) -> None:
        assert dc_client._api_base == "https://bitbucket.example.com/rest/api/1.0"


# ---------------------------------------------------------------------------
# Helper URL methods
# ---------------------------------------------------------------------------

class TestURLHelpers:
    def test_dc_project_repo_url(self, dc_client: BitbucketClient) -> None:
        url = dc_client._dc_project_repo_url("PROJ", "my-repo")
        assert url == "https://bitbucket.example.com/rest/api/1.0/projects/PROJ/repos/my-repo"

    def test_cloud_repo_url(self, cloud_client: BitbucketClient) -> None:
        url = cloud_client._cloud_repo_url("my-repo")
        assert url == "https://api.bitbucket.org/2.0/repositories/myworkspace/my-repo"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_dc_health_check(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(200, {"version": "8.0"})):
            result = dc_client.health_check()
        assert result["connected"] is True
        assert result["auth_type"] == "pat"

    def test_cloud_health_check(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, {"username": "u"})):
            result = cloud_client.health_check()
        assert result["connected"] is True
        assert result["auth_type"] == "cloud"

    def test_health_check_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(401)):
            with pytest.raises(ValueError, match="Authentication failed"):
                dc_client.health_check()

    def test_health_check_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Connection timeout"):
                dc_client.health_check()

    def test_health_check_network_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.NetworkError("dns fail")):
            with pytest.raises(ValueError, match="Network error"):
                dc_client.health_check()


# ---------------------------------------------------------------------------
# Project operations
# ---------------------------------------------------------------------------

class TestProjectOperations:
    def test_list_projects(self, dc_client: BitbucketClient) -> None:
        data = {"values": [{"key": "PROJ"}]}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.list_projects(limit=10, start=0)
        assert result == data

    def test_list_projects_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(403)):
            with pytest.raises(ValueError, match="Permission denied"):
                dc_client.list_projects()

    def test_list_projects_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing projects"):
                dc_client.list_projects()

    def test_get_project(self, dc_client: BitbucketClient) -> None:
        data = {"key": "PROJ", "name": "Project"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_project("PROJ")
        assert result == data

    def test_get_project_not_found(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_project("MISSING")

    def test_get_project_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting project"):
                dc_client.get_project("PROJ")

    def test_create_project(self, dc_client: BitbucketClient) -> None:
        data = {"key": "NEW", "name": "New Project"}
        with patch.object(dc_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = dc_client.create_project("NEW", "New Project", "A description")
        assert result == data
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["json"]["description"] == "A description"

    def test_create_project_no_description(self, dc_client: BitbucketClient) -> None:
        data = {"key": "NEW"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            dc_client.create_project("NEW", "New Project")
        payload = mock_req.call_args.kwargs["json"]
        assert "description" not in payload

    def test_create_project_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(409, text="Conflict: key exists")):
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.create_project("DUP", "Dup")

    def test_create_project_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating project"):
                dc_client.create_project("X", "X")


# ---------------------------------------------------------------------------
# Repository operations
# ---------------------------------------------------------------------------

class TestRepoOperations:
    # --- list_repos ---
    def test_list_repos_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.list_repos("PROJ", limit=10, start=5)
        assert result == data
        params = mock_req.call_args.kwargs["params"]
        assert params["limit"] == 10
        assert params["start"] == 5

    def test_list_repos_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.list_repos("ignored", limit=10, start=0)
        assert result == data
        params = mock_req.call_args.kwargs["params"]
        assert params["pagelen"] == 10

    def test_list_repos_cloud_pagination(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, {})) as mock_req:
            cloud_client.list_repos("ignored", limit=10, start=20)
        params = mock_req.call_args.kwargs["params"]
        assert params["page"] == 3

    def test_list_repos_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing repos"):
                dc_client.list_repos("PROJ")

    def test_list_repos_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(403)):
            with pytest.raises(ValueError, match="Permission denied"):
                dc_client.list_repos("PROJ")

    # --- get_repo ---
    def test_get_repo_dc(self, dc_client: BitbucketClient) -> None:
        data = {"slug": "my-repo"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_repo("PROJ", "my-repo")
        assert result == data

    def test_get_repo_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"slug": "my-repo"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.get_repo("ignored", "my-repo")
        assert result == data

    def test_get_repo_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting repo"):
                dc_client.get_repo("PROJ", "r")

    def test_get_repo_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_repo("PROJ", "missing")

    # --- create_repo ---
    def test_create_repo_dc(self, dc_client: BitbucketClient) -> None:
        data = {"slug": "new-repo"}
        with patch.object(dc_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = dc_client.create_repo("PROJ", "new-repo", "desc")
        assert result == data
        assert mock_req.call_args.args[0] == "POST"
        assert mock_req.call_args.kwargs["json"]["scmId"] == "git"

    def test_create_repo_dc_no_description(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(201, {})) as mock_req:
            dc_client.create_repo("PROJ", "new-repo")
        assert "description" not in mock_req.call_args.kwargs["json"]

    def test_create_repo_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"slug": "new-repo"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.create_repo("ignored", "new-repo", "desc")
        assert result == data
        assert mock_req.call_args.args[0] == "PUT"
        assert mock_req.call_args.kwargs["json"]["scm"] == "git"

    def test_create_repo_cloud_no_description(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, {})) as mock_req:
            cloud_client.create_repo("ignored", "new-repo")
        assert "description" not in mock_req.call_args.kwargs["json"]

    def test_create_repo_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating repo"):
                dc_client.create_repo("PROJ", "r")

    def test_create_repo_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(409, text="exists")):
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.create_repo("PROJ", "r")

    # --- delete_repo ---
    def test_delete_repo_dc(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(202)):
            dc_client.delete_repo("PROJ", "my-repo")

    def test_delete_repo_cloud(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(204)):
            cloud_client.delete_repo("ignored", "my-repo")

    def test_delete_repo_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.delete_repo("PROJ", "missing")

    def test_delete_repo_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting repo"):
                dc_client.delete_repo("PROJ", "r")

    # --- fork_repo ---
    def test_fork_repo_dc(self, dc_client: BitbucketClient) -> None:
        data = {"slug": "fork"}
        with patch.object(dc_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = dc_client.fork_repo("PROJ", "repo", "fork")
        assert result == data
        assert mock_req.call_args.kwargs["json"]["name"] == "fork"

    def test_fork_repo_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"slug": "fork"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.fork_repo("ignored", "repo", "fork")
        assert result == data

    def test_fork_repo_no_name(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(201, {})) as mock_req:
            dc_client.fork_repo("PROJ", "repo")
        assert "name" not in mock_req.call_args.kwargs["json"]

    def test_fork_repo_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout forking repo"):
                dc_client.fork_repo("PROJ", "r")

    def test_fork_repo_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(403)):
            with pytest.raises(ValueError, match="Permission denied"):
                dc_client.fork_repo("PROJ", "r")


# ---------------------------------------------------------------------------
# Branch operations
# ---------------------------------------------------------------------------

class TestBranchOperations:
    def test_list_branches_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": [{"displayId": "main"}]}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.list_branches("PROJ", "repo", limit=10, start=5)
        assert result == data
        params = mock_req.call_args.kwargs["params"]
        assert params["limit"] == 10
        assert params["start"] == 5

    def test_list_branches_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": [{"name": "main"}]}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.list_branches("ignored", "repo", limit=10)
        assert result == data
        assert mock_req.call_args.kwargs["params"]["pagelen"] == 10

    def test_list_branches_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing branches"):
                dc_client.list_branches("PROJ", "repo")

    def test_list_branches_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.list_branches("PROJ", "repo")

    def test_create_branch_dc(self, dc_client: BitbucketClient) -> None:
        data = {"displayId": "feature"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.create_branch("PROJ", "repo", "feature", "abc123")
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["name"] == "feature"
        assert payload["startPoint"] == "abc123"

    def test_create_branch_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"name": "feature"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = cloud_client.create_branch("ignored", "repo", "feature", "abc123")
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["target"]["hash"] == "abc123"

    def test_create_branch_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating branch"):
                dc_client.create_branch("PROJ", "repo", "b", "abc")

    def test_create_branch_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(409, text="exists")):
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.create_branch("PROJ", "repo", "b", "abc")

    def test_delete_branch_dc(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(204)) as mock_req:
            dc_client.delete_branch("PROJ", "repo", "feature")
        payload = mock_req.call_args.kwargs["json"]
        assert payload["name"] == "feature"
        assert payload["dryRun"] is False

    def test_delete_branch_cloud(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(204)):
            cloud_client.delete_branch("ignored", "repo", "feature")

    def test_delete_branch_dc_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.delete_branch("PROJ", "repo", "missing")

    def test_delete_branch_cloud_error(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                cloud_client.delete_branch("ignored", "repo", "missing")

    def test_delete_branch_dc_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting branch"):
                dc_client.delete_branch("PROJ", "repo", "b")

    def test_delete_branch_cloud_timeout(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting branch"):
                cloud_client.delete_branch("ignored", "repo", "b")

    def test_get_default_branch_dc(self, dc_client: BitbucketClient) -> None:
        data = {"displayId": "main", "id": "refs/heads/main"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_default_branch("PROJ", "repo")
        assert result == data

    def test_get_default_branch_cloud(self, cloud_client: BitbucketClient) -> None:
        repo_data = {"mainbranch": {"name": "develop"}}
        with patch.object(cloud_client, "get_repo", return_value=repo_data):
            result = cloud_client.get_default_branch("ignored", "repo")
        assert result == {"name": "develop"}

    def test_get_default_branch_cloud_missing_mainbranch(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "get_repo", return_value={}):
            result = cloud_client.get_default_branch("ignored", "repo")
        assert result == {"name": "main"}

    def test_get_default_branch_dc_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting default branch"):
                dc_client.get_default_branch("PROJ", "repo")

    def test_get_default_branch_dc_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_default_branch("PROJ", "repo")


# ---------------------------------------------------------------------------
# Commit operations
# ---------------------------------------------------------------------------

class TestCommitOperations:
    def test_list_commits_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.list_commits("PROJ", "repo", branch="main", limit=5, start=0)
        assert result == data
        params = mock_req.call_args.kwargs["params"]
        assert params["until"] == "main"

    def test_list_commits_dc_no_branch(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(200, {})) as mock_req:
            dc_client.list_commits("PROJ", "repo")
        params = mock_req.call_args.kwargs["params"]
        assert "until" not in params

    def test_list_commits_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.list_commits("ignored", "repo", branch="main")
        assert result == data
        params = mock_req.call_args.kwargs["params"]
        assert params["include"] == "main"

    def test_list_commits_cloud_no_branch(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, {})) as mock_req:
            cloud_client.list_commits("ignored", "repo")
        params = mock_req.call_args.kwargs["params"]
        assert "include" not in params

    def test_list_commits_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing commits"):
                dc_client.list_commits("PROJ", "repo")

    def test_list_commits_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.list_commits("PROJ", "repo")

    def test_get_commit_dc(self, dc_client: BitbucketClient) -> None:
        data = {"id": "abc123"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_commit("PROJ", "repo", "abc123")
        assert result == data

    def test_get_commit_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"hash": "abc123"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.get_commit("ignored", "repo", "abc123")
        assert result == data

    def test_get_commit_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting commit"):
                dc_client.get_commit("PROJ", "repo", "abc")

    def test_get_commit_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_commit("PROJ", "repo", "abc")

    def test_get_commit_diff_dc(self, dc_client: BitbucketClient) -> None:
        data = {"diffs": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_commit_diff("PROJ", "repo", "abc123")
        assert result == data

    def test_get_commit_diff_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"diffs": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.get_commit_diff("ignored", "repo", "abc123")
        assert result == data

    def test_get_commit_diff_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting diff for commit"):
                dc_client.get_commit_diff("PROJ", "repo", "abc")

    def test_get_commit_diff_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_commit_diff("PROJ", "repo", "abc")


# ---------------------------------------------------------------------------
# PR operations
# ---------------------------------------------------------------------------

class TestPROperations:
    # --- list_prs ---
    def test_list_prs_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.list_prs("PROJ", "repo", state="MERGED", limit=10, start=5)
        assert result == data
        params = mock_req.call_args.kwargs["params"]
        assert params["state"] == "MERGED"

    def test_list_prs_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.list_prs("ignored", "repo")
        assert result == data
        params = mock_req.call_args.kwargs["params"]
        assert params["pagelen"] == 25

    def test_list_prs_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing PRs"):
                dc_client.list_prs("PROJ", "repo")

    def test_list_prs_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(403)):
            with pytest.raises(ValueError, match="Permission denied"):
                dc_client.list_prs("PROJ", "repo")

    # --- get_pr ---
    def test_get_pr_dc(self, dc_client: BitbucketClient) -> None:
        data = {"id": 1, "title": "PR"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_pr("PROJ", "repo", 1)
        assert result == data

    def test_get_pr_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"id": 1}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.get_pr("ignored", "repo", 1)
        assert result == data

    def test_get_pr_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting PR"):
                dc_client.get_pr("PROJ", "repo", 1)

    def test_get_pr_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_pr("PROJ", "repo", 999)

    # --- create_pr ---
    def test_create_pr_dc(self, dc_client: BitbucketClient) -> None:
        data = {"id": 1}
        with patch.object(dc_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = dc_client.create_pr("PROJ", "repo", "title", "feature", "main", "desc")
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["fromRef"]["id"] == "refs/heads/feature"
        assert payload["toRef"]["id"] == "refs/heads/main"
        assert payload["description"] == "desc"

    def test_create_pr_dc_no_description(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(201, {})) as mock_req:
            dc_client.create_pr("PROJ", "repo", "title", "feature", "main")
        assert "description" not in mock_req.call_args.kwargs["json"]

    def test_create_pr_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"id": 1}
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = cloud_client.create_pr("ignored", "repo", "title", "feature", "main", "desc")
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["source"]["branch"]["name"] == "feature"
        assert payload["destination"]["branch"]["name"] == "main"

    def test_create_pr_cloud_no_description(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, {})) as mock_req:
            cloud_client.create_pr("ignored", "repo", "title", "feature", "main")
        assert "description" not in mock_req.call_args.kwargs["json"]

    def test_create_pr_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating PR"):
                dc_client.create_pr("PROJ", "repo", "t", "f", "m")

    def test_create_pr_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(409, text="conflict")):
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.create_pr("PROJ", "repo", "t", "f", "m")

    def test_create_pr_dc_with_reviewers(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(201, {"id": 1})) as mock_req:
            dc_client.create_pr("PROJ", "repo", "title", "feature", "main", reviewers=["alice", "bob"])
        payload = mock_req.call_args.kwargs["json"]
        assert payload["reviewers"] == [{"user": {"name": "alice"}}, {"user": {"name": "bob"}}]

    def test_create_pr_cloud_with_reviewers(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, {"id": 1})) as mock_req:
            cloud_client.create_pr("ignored", "repo", "title", "feature", "main", reviewers=["{uuid-1}"])
        payload = mock_req.call_args.kwargs["json"]
        assert payload["reviewers"] == [{"uuid": "{uuid-1}"}]

    def test_create_pr_dc_no_reviewers(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(201, {})) as mock_req:
            dc_client.create_pr("PROJ", "repo", "t", "f", "m")
        assert "reviewers" not in mock_req.call_args.kwargs["json"]

    # --- update_pr ---
    def test_update_pr_dc(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 3}
        update_data = {"id": 1, "version": 4, "title": "new"}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, update_data)]
            result = dc_client.update_pr("PROJ", "repo", 1, title="new")
        assert result == update_data
        put_payload = mock_req.call_args_list[1].kwargs["json"]
        assert put_payload["version"] == 3
        assert put_payload["title"] == "new"

    def test_update_pr_cloud(self, cloud_client: BitbucketClient) -> None:
        pr_data = {"id": 1}
        update_data = {"id": 1, "title": "new", "description": "d"}
        with patch.object(cloud_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, update_data)]
            result = cloud_client.update_pr("ignored", "repo", 1, title="new", description="d")
        assert result == update_data
        put_payload = mock_req.call_args_list[1].kwargs["json"]
        assert "version" not in put_payload

    def test_update_pr_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"id": 1, "version": 0}), httpx.TimeoutException("t")]
            with pytest.raises(ValueError, match="Timeout updating PR"):
                dc_client.update_pr("PROJ", "repo", 1, title="x")

    def test_update_pr_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"id": 1, "version": 0}), _mock_response(409, text="conflict")]
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.update_pr("PROJ", "repo", 1, title="x")

    # --- merge_pr ---
    def test_merge_pr_dc(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 2}
        merge_data = {"id": 1, "state": "MERGED"}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, merge_data)]
            result = dc_client.merge_pr("PROJ", "repo", 1, message="merge msg")
        assert result == merge_data
        payload = mock_req.call_args_list[1].kwargs["json"]
        assert payload["version"] == 2
        assert payload["message"] == "merge msg"

    def test_merge_pr_dc_no_message(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"version": 0}), _mock_response(200, {})]
            dc_client.merge_pr("PROJ", "repo", 1)
        payload = mock_req.call_args_list[1].kwargs["json"]
        assert "message" not in payload

    def test_merge_pr_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"state": "MERGED"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.merge_pr("ignored", "repo", 1, message="msg")
        assert result == data
        assert mock_req.call_args.kwargs["json"]["message"] == "msg"

    def test_merge_pr_cloud_no_message(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, {})) as mock_req:
            cloud_client.merge_pr("ignored", "repo", 1)
        assert mock_req.call_args.kwargs["json"] == {}

    def test_merge_pr_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"version": 0}), httpx.TimeoutException("t")]
            with pytest.raises(ValueError, match="Timeout merging PR"):
                dc_client.merge_pr("PROJ", "repo", 1)

    def test_merge_pr_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"version": 0}), _mock_response(409, text="conflict")]
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.merge_pr("PROJ", "repo", 1)

    # --- decline_pr ---
    def test_decline_pr_dc(self, dc_client: BitbucketClient) -> None:
        decline_data = {"id": 1, "state": "DECLINED"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, decline_data)):
            result = dc_client.decline_pr("PROJ", "repo", 1)
        assert result == decline_data

    def test_decline_pr_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"state": "DECLINED"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.decline_pr("ignored", "repo", 1)
        assert result == data

    def test_decline_pr_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout declining PR"):
                dc_client.decline_pr("PROJ", "repo", 1)

    def test_decline_pr_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(409, text="conflict")):
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.decline_pr("PROJ", "repo", 1)

    # --- reopen_pr ---
    def test_reopen_pr_dc(self, dc_client: BitbucketClient) -> None:
        data = {"id": 1, "state": "OPEN"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.reopen_pr("PROJ", "repo", 1)
        assert result == data

    def test_reopen_pr_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"id": 1, "state": "OPEN"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.reopen_pr("ignored", "repo", 1)
        assert result == data
        assert mock_req.call_args.kwargs["json"]["state"] == "OPEN"

    def test_reopen_pr_dc_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(409, text="conflict")):
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.reopen_pr("PROJ", "repo", 1)

    def test_reopen_pr_cloud_error(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(409, text="conflict")):
            with pytest.raises(ValueError, match="Conflict"):
                cloud_client.reopen_pr("ignored", "repo", 1)

    def test_reopen_pr_dc_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout reopening PR"):
                dc_client.reopen_pr("PROJ", "repo", 1)

    def test_reopen_pr_cloud_timeout(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout reopening PR"):
                cloud_client.reopen_pr("ignored", "repo", 1)

    # --- get_pr_diff ---
    def test_get_pr_diff_dc(self, dc_client: BitbucketClient) -> None:
        data = {"diffs": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_pr_diff("PROJ", "repo", 1)
        assert result == data

    def test_get_pr_diff_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"diffs": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.get_pr_diff("ignored", "repo", 1)
        assert result == data

    def test_get_pr_diff_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting PR .* diff"):
                dc_client.get_pr_diff("PROJ", "repo", 1)

    def test_get_pr_diff_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_pr_diff("PROJ", "repo", 1)

    # --- get_pr_commits ---
    def test_get_pr_commits_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_pr_commits("PROJ", "repo", 1)
        assert result == data

    def test_get_pr_commits_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.get_pr_commits("ignored", "repo", 1)
        assert result == data

    def test_get_pr_commits_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting PR .* commits"):
                dc_client.get_pr_commits("PROJ", "repo", 1)

    def test_get_pr_commits_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_pr_commits("PROJ", "repo", 1)

    # --- get_pr_activities ---
    def test_get_pr_activities_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_pr_activities("PROJ", "repo", 1)
        assert result == data

    def test_get_pr_activities_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.get_pr_activities("ignored", "repo", 1)
        assert result == data

    def test_get_pr_activities_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting PR .* activities"):
                dc_client.get_pr_activities("PROJ", "repo", 1)

    def test_get_pr_activities_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_pr_activities("PROJ", "repo", 1)


# ---------------------------------------------------------------------------
# PR Comment operations
# ---------------------------------------------------------------------------

class TestPRCommentOperations:
    # --- add_pr_comment ---
    def test_add_pr_comment_dc(self, dc_client: BitbucketClient) -> None:
        data = {"id": 10, "text": "nice"}
        with patch.object(dc_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = dc_client.add_pr_comment("PROJ", "repo", 1, "nice")
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["text"] == "nice"
        assert "anchor" not in payload

    def test_add_pr_comment_dc_inline(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(201, {})) as mock_req:
            dc_client.add_pr_comment("PROJ", "repo", 1, "fix this", file_path="src/main.py", line=42)
        payload = mock_req.call_args.kwargs["json"]
        assert payload["anchor"]["path"] == "src/main.py"
        assert payload["anchor"]["line"] == 42
        assert payload["anchor"]["lineType"] == "ADDED"

    def test_add_pr_comment_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"id": 10}
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = cloud_client.add_pr_comment("ignored", "repo", 1, "nice")
        assert result == data
        assert mock_req.call_args.kwargs["json"]["content"]["raw"] == "nice"

    def test_add_pr_comment_cloud_inline(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, {})) as mock_req:
            cloud_client.add_pr_comment("ignored", "repo", 1, "fix", file_path="main.py", line=10)
        payload = mock_req.call_args.kwargs["json"]
        assert payload["inline"]["path"] == "main.py"
        assert payload["inline"]["to"] == 10

    def test_add_pr_comment_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout adding comment"):
                dc_client.add_pr_comment("PROJ", "repo", 1, "text")

    def test_add_pr_comment_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(403)):
            with pytest.raises(ValueError, match="Permission denied"):
                dc_client.add_pr_comment("PROJ", "repo", 1, "text")

    # --- list_pr_comments ---
    def test_list_pr_comments_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.list_pr_comments("PROJ", "repo", 1)
        assert result == data

    def test_list_pr_comments_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.list_pr_comments("ignored", "repo", 1)
        assert result == data

    def test_list_pr_comments_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing PR .* comments"):
                dc_client.list_pr_comments("PROJ", "repo", 1)

    def test_list_pr_comments_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.list_pr_comments("PROJ", "repo", 1)

    # --- update_pr_comment ---
    def test_update_pr_comment_dc(self, dc_client: BitbucketClient) -> None:
        comment_data = {"id": 5, "version": 2, "text": "old"}
        updated = {"id": 5, "text": "new"}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, comment_data), _mock_response(200, updated)]
            result = dc_client.update_pr_comment("PROJ", "repo", 1, 5, "new")
        assert result == updated
        put_payload = mock_req.call_args_list[1].kwargs["json"]
        assert put_payload["version"] == 2

    def test_update_pr_comment_cloud(self, cloud_client: BitbucketClient) -> None:
        updated = {"id": 5}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, updated)) as mock_req:
            result = cloud_client.update_pr_comment("ignored", "repo", 1, 5, "new")
        assert result == updated
        assert mock_req.call_args.kwargs["json"]["content"]["raw"] == "new"

    def test_update_pr_comment_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"version": 0}), httpx.TimeoutException("t")]
            with pytest.raises(ValueError, match="Timeout updating PR comment"):
                dc_client.update_pr_comment("PROJ", "repo", 1, 5, "new")

    def test_update_pr_comment_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"version": 0}), _mock_response(404)]
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.update_pr_comment("PROJ", "repo", 1, 5, "new")

    # --- delete_pr_comment ---
    def test_delete_pr_comment_dc(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"version": 1}), _mock_response(204)]
            dc_client.delete_pr_comment("PROJ", "repo", 1, 5)

    def test_delete_pr_comment_cloud(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(204)):
            cloud_client.delete_pr_comment("ignored", "repo", 1, 5)

    def test_delete_pr_comment_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"version": 0}), httpx.TimeoutException("t")]
            with pytest.raises(ValueError, match="Timeout deleting PR comment"):
                dc_client.delete_pr_comment("PROJ", "repo", 1, 5)

    def test_delete_pr_comment_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, {"version": 0}), _mock_response(404)]
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.delete_pr_comment("PROJ", "repo", 1, 5)


# ---------------------------------------------------------------------------
# PR Review operations
# ---------------------------------------------------------------------------

class TestPRReviewOperations:
    def test_approve_pr_dc(self, dc_client: BitbucketClient) -> None:
        data = {"approved": True}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.approve_pr("PROJ", "repo", 1)
        assert result == data

    def test_approve_pr_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"approved": True}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.approve_pr("ignored", "repo", 1)
        assert result == data

    def test_approve_pr_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout approving PR"):
                dc_client.approve_pr("PROJ", "repo", 1)

    def test_approve_pr_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(409, text="conflict")):
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.approve_pr("PROJ", "repo", 1)

    def test_unapprove_pr_dc(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(204)):
            dc_client.unapprove_pr("PROJ", "repo", 1)

    def test_unapprove_pr_cloud(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(200)):
            cloud_client.unapprove_pr("ignored", "repo", 1)

    def test_unapprove_pr_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout unapproving PR"):
                dc_client.unapprove_pr("PROJ", "repo", 1)

    def test_unapprove_pr_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(403)):
            with pytest.raises(ValueError, match="Permission denied"):
                dc_client.unapprove_pr("PROJ", "repo", 1)

    def test_needs_work_pr(self, dc_client: BitbucketClient) -> None:
        data = {"status": "NEEDS_WORK"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.needs_work_pr("PROJ", "repo", 1)
        assert result == data
        assert mock_req.call_args.kwargs["json"]["status"] == "NEEDS_WORK"

    def test_needs_work_pr_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout marking PR .* needs work"):
                dc_client.needs_work_pr("PROJ", "repo", 1)

    def test_needs_work_pr_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.needs_work_pr("PROJ", "repo", 1)


# ---------------------------------------------------------------------------
# PR Reviewer operations
# ---------------------------------------------------------------------------


class TestPRReviewerOperations:
    # --- get_pr_reviewers ---

    def test_get_pr_reviewers_dc(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "reviewers": [{"user": {"name": "alice"}}, {"user": {"name": "bob"}}]}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, pr_data)):
            result = dc_client.get_pr_reviewers("PROJ", "repo", 1)
        assert len(result["reviewers"]) == 2
        assert result["reviewers"][0]["user"]["name"] == "alice"

    def test_get_pr_reviewers_cloud(self, cloud_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "reviewers": [{"uuid": "{uuid-1}", "display_name": "Alice"}]}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, pr_data)):
            result = cloud_client.get_pr_reviewers("ignored", "repo", 1)
        assert len(result["reviewers"]) == 1
        assert result["reviewers"][0]["uuid"] == "{uuid-1}"

    def test_get_pr_reviewers_empty(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "reviewers": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, pr_data)):
            result = dc_client.get_pr_reviewers("PROJ", "repo", 1)
        assert result["reviewers"] == []

    def test_get_pr_reviewers_no_key(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, pr_data)):
            result = dc_client.get_pr_reviewers("PROJ", "repo", 1)
        assert result["reviewers"] == []

    # --- add_pr_reviewer ---

    def test_add_pr_reviewer_dc(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 5, "reviewers": [{"user": {"name": "alice"}}]}
        updated = {"id": 1, "version": 6, "reviewers": [{"user": {"name": "alice"}}, {"user": {"name": "bob"}}]}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, updated)]
            result = dc_client.add_pr_reviewer("PROJ", "repo", 1, "bob")
        assert result == updated
        put_payload = mock_req.call_args_list[1].kwargs["json"]
        assert put_payload["version"] == 5
        assert len(put_payload["reviewers"]) == 2
        assert put_payload["reviewers"][1]["user"]["name"] == "bob"

    def test_add_pr_reviewer_cloud(self, cloud_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "reviewers": [{"uuid": "{uuid-1}"}]}
        updated = {"id": 1, "reviewers": [{"uuid": "{uuid-1}"}, {"uuid": "{uuid-2}"}]}
        with patch.object(cloud_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, updated)]
            result = cloud_client.add_pr_reviewer("ignored", "repo", 1, "{uuid-2}")
        assert result == updated
        put_payload = mock_req.call_args_list[1].kwargs["json"]
        assert "version" not in put_payload
        assert put_payload["reviewers"][1]["uuid"] == "{uuid-2}"

    def test_add_pr_reviewer_to_empty(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 0, "reviewers": []}
        updated = {"id": 1, "version": 1, "reviewers": [{"user": {"name": "alice"}}]}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, updated)]
            result = dc_client.add_pr_reviewer("PROJ", "repo", 1, "alice")
        assert len(result["reviewers"]) == 1

    def test_add_pr_reviewer_timeout(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 0, "reviewers": []}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), httpx.TimeoutException("t")]
            with pytest.raises(ValueError, match="Timeout adding reviewer to PR"):
                dc_client.add_pr_reviewer("PROJ", "repo", 1, "alice")

    def test_add_pr_reviewer_error(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 0, "reviewers": []}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(404)]
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.add_pr_reviewer("PROJ", "repo", 1, "alice")

    # --- remove_pr_reviewer ---

    def test_remove_pr_reviewer_dc(self, dc_client: BitbucketClient) -> None:
        pr_data = {
            "id": 1, "version": 3,
            "reviewers": [{"user": {"name": "alice"}}, {"user": {"name": "bob"}}],
        }
        updated = {"id": 1, "version": 4, "reviewers": [{"user": {"name": "bob"}}]}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, updated)]
            result = dc_client.remove_pr_reviewer("PROJ", "repo", 1, "alice")
        assert result == updated
        put_payload = mock_req.call_args_list[1].kwargs["json"]
        assert put_payload["version"] == 3
        assert len(put_payload["reviewers"]) == 1
        assert put_payload["reviewers"][0]["user"]["name"] == "bob"

    def test_remove_pr_reviewer_cloud(self, cloud_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "reviewers": [{"uuid": "{uuid-1}"}, {"uuid": "{uuid-2}"}]}
        updated = {"id": 1, "reviewers": [{"uuid": "{uuid-2}"}]}
        with patch.object(cloud_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, updated)]
            result = cloud_client.remove_pr_reviewer("ignored", "repo", 1, "{uuid-1}")
        assert result == updated
        put_payload = mock_req.call_args_list[1].kwargs["json"]
        assert len(put_payload["reviewers"]) == 1
        assert put_payload["reviewers"][0]["uuid"] == "{uuid-2}"

    def test_remove_pr_reviewer_not_found(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 0, "reviewers": [{"user": {"name": "alice"}}]}
        updated = {"id": 1, "version": 1, "reviewers": [{"user": {"name": "alice"}}]}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(200, updated)]
            dc_client.remove_pr_reviewer("PROJ", "repo", 1, "nonexistent")
        put_payload = mock_req.call_args_list[1].kwargs["json"]
        assert len(put_payload["reviewers"]) == 1

    def test_remove_pr_reviewer_timeout(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 0, "reviewers": [{"user": {"name": "alice"}}]}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), httpx.TimeoutException("t")]
            with pytest.raises(ValueError, match="Timeout removing reviewer from PR"):
                dc_client.remove_pr_reviewer("PROJ", "repo", 1, "alice")

    def test_remove_pr_reviewer_error(self, dc_client: BitbucketClient) -> None:
        pr_data = {"id": 1, "version": 0, "reviewers": [{"user": {"name": "alice"}}]}
        with patch.object(dc_client, "_request") as mock_req:
            mock_req.side_effect = [_mock_response(200, pr_data), _mock_response(409, text="conflict")]
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.remove_pr_reviewer("PROJ", "repo", 1, "alice")


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

class TestFileOperations:
    def test_browse_files_dc(self, dc_client: BitbucketClient) -> None:
        data = {"children": {"values": []}}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.browse_files("PROJ", "repo", path="src", at="main")
        assert result == data
        assert mock_req.call_args.kwargs["params"]["at"] == "main"

    def test_browse_files_dc_no_at(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(200, {})) as mock_req:
            dc_client.browse_files("PROJ", "repo")
        assert mock_req.call_args.kwargs["params"] == {}

    def test_browse_files_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.browse_files("ignored", "repo", path="src", at="main")
        assert result == data
        url = mock_req.call_args.args[1]
        assert "/src/main/src" in url

    def test_browse_files_cloud_no_path_no_at(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, {})) as mock_req:
            cloud_client.browse_files("ignored", "repo")
        url = mock_req.call_args.args[1]
        assert url.endswith("/src")

    def test_browse_files_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout browsing files"):
                dc_client.browse_files("PROJ", "repo")

    def test_browse_files_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.browse_files("PROJ", "repo", path="missing")

    def test_get_file_content_dc(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(200, text="file content", headers={"content-type": "text/plain"})
        resp.json.side_effect = ValueError("not json")
        with patch.object(dc_client, "_request", return_value=resp) as mock_req:
            result = dc_client.get_file_content("PROJ", "repo", "README.md", at="main")
        assert result == {"content": "file content", "path": "README.md"}
        assert mock_req.call_args.kwargs["params"]["at"] == "main"

    def test_get_file_content_dc_json(self, dc_client: BitbucketClient) -> None:
        data = {"lines": [{"text": "hello"}]}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.get_file_content("PROJ", "repo", "data.json")
        assert result == data

    def test_get_file_content_cloud(self, cloud_client: BitbucketClient) -> None:
        resp = _mock_response(200, text="content", headers={"content-type": "text/plain"})
        resp.json.side_effect = ValueError("not json")
        with patch.object(cloud_client, "_request", return_value=resp) as mock_req:
            result = cloud_client.get_file_content("ignored", "repo", "file.txt", at="dev")
        assert result["content"] == "content"
        url = mock_req.call_args.args[1]
        assert "/src/dev/file.txt" in url

    def test_get_file_content_cloud_no_at(self, cloud_client: BitbucketClient) -> None:
        resp = _mock_response(200, text="x", headers={"content-type": "text/plain"})
        resp.json.side_effect = ValueError("not json")
        with patch.object(cloud_client, "_request", return_value=resp) as mock_req:
            cloud_client.get_file_content("ignored", "repo", "file.txt")
        url = mock_req.call_args.args[1]
        assert url.endswith("/src/file.txt")

    def test_get_file_content_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting file"):
                dc_client.get_file_content("PROJ", "repo", "f.txt")

    def test_get_file_content_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_file_content("PROJ", "repo", "missing.txt")


# ---------------------------------------------------------------------------
# Tag operations
# ---------------------------------------------------------------------------

class TestTagOperations:
    def test_list_tags_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.list_tags("PROJ", "repo", limit=10, start=5)
        assert result == data
        params = mock_req.call_args.kwargs["params"]
        assert params["limit"] == 10

    def test_list_tags_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.list_tags("ignored", "repo")
        assert result == data
        assert mock_req.call_args.kwargs["params"]["pagelen"] == 25

    def test_list_tags_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing tags"):
                dc_client.list_tags("PROJ", "repo")

    def test_list_tags_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.list_tags("PROJ", "repo")

    def test_create_tag_dc(self, dc_client: BitbucketClient) -> None:
        data = {"name": "v1.0"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.create_tag("PROJ", "repo", "v1.0", "abc123", "release")
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["startPoint"] == "abc123"
        assert payload["message"] == "release"

    def test_create_tag_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"name": "v1.0"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = cloud_client.create_tag("ignored", "repo", "v1.0", "abc123")
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["target"]["hash"] == "abc123"

    def test_create_tag_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating tag"):
                dc_client.create_tag("PROJ", "repo", "v1", "abc")

    def test_create_tag_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(409, text="exists")):
            with pytest.raises(ValueError, match="Conflict"):
                dc_client.create_tag("PROJ", "repo", "v1", "abc")

    def test_delete_tag_dc(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(204)):
            dc_client.delete_tag("PROJ", "repo", "v1.0")

    def test_delete_tag_cloud(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(204)):
            cloud_client.delete_tag("ignored", "repo", "v1.0")

    def test_delete_tag_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting tag"):
                dc_client.delete_tag("PROJ", "repo", "v1")

    def test_delete_tag_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.delete_tag("PROJ", "repo", "missing")


# ---------------------------------------------------------------------------
# Webhook operations
# ---------------------------------------------------------------------------

class TestWebhookOperations:
    def test_list_webhooks_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)):
            result = dc_client.list_webhooks("PROJ", "repo")
        assert result == data

    def test_list_webhooks_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)):
            result = cloud_client.list_webhooks("ignored", "repo")
        assert result == data

    def test_list_webhooks_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout listing webhooks"):
                dc_client.list_webhooks("PROJ", "repo")

    def test_list_webhooks_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.list_webhooks("PROJ", "repo")

    def test_create_webhook_dc(self, dc_client: BitbucketClient) -> None:
        data = {"id": 1}
        with patch.object(dc_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = dc_client.create_webhook("PROJ", "repo", "hook", "https://example.com", ["push"])
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["name"] == "hook"
        assert payload["events"] == ["push"]

    def test_create_webhook_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"uuid": "abc"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = cloud_client.create_webhook("ignored", "repo", "hook", "https://example.com", ["push"])
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["description"] == "hook"

    def test_create_webhook_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout creating webhook"):
                dc_client.create_webhook("PROJ", "repo", "h", "https://x.com", ["push"])

    def test_create_webhook_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(403)):
            with pytest.raises(ValueError, match="Permission denied"):
                dc_client.create_webhook("PROJ", "repo", "h", "https://x.com", ["push"])

    def test_delete_webhook_dc(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(204)):
            dc_client.delete_webhook("PROJ", "repo", "123")

    def test_delete_webhook_cloud(self, cloud_client: BitbucketClient) -> None:
        with patch.object(cloud_client, "_request", return_value=_mock_response(204)):
            cloud_client.delete_webhook("ignored", "repo", "abc-uuid")

    def test_delete_webhook_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout deleting webhook"):
                dc_client.delete_webhook("PROJ", "repo", "123")

    def test_delete_webhook_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.delete_webhook("PROJ", "repo", "missing")


# ---------------------------------------------------------------------------
# Build status operations
# ---------------------------------------------------------------------------

class TestBuildStatusOperations:
    def test_get_build_status_dc(self, dc_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.get_build_status("abc123")
        assert result == data
        url = mock_req.call_args.args[1]
        assert "/rest/build-status/1.0/commits/abc123" in url

    def test_get_build_status_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"values": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.get_build_status("abc123")
        assert result == data
        url = mock_req.call_args.args[1]
        assert "/repositories/myworkspace/commit/abc123/statuses" in url

    def test_get_build_status_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting build status"):
                dc_client.get_build_status("abc")

    def test_get_build_status_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_build_status("abc")

    def test_set_build_status_dc(self, dc_client: BitbucketClient) -> None:
        data = {"state": "SUCCESSFUL"}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.set_build_status("abc", "SUCCESSFUL", "build-1", "https://ci.com/1", "passed")
        assert result == data
        payload = mock_req.call_args.kwargs["json"]
        assert payload["state"] == "SUCCESSFUL"
        assert payload["key"] == "build-1"
        assert payload["description"] == "passed"

    def test_set_build_status_dc_no_description(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(201, {})) as mock_req:
            dc_client.set_build_status("abc", "FAILED", "k", "https://ci.com")
        assert "description" not in mock_req.call_args.kwargs["json"]

    def test_set_build_status_dc_204(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(204)):
            result = dc_client.set_build_status("abc", "SUCCESSFUL", "k", "https://ci.com")
        assert result == {"success": True}

    def test_set_build_status_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"state": "SUCCESSFUL"}
        with patch.object(cloud_client, "_request", return_value=_mock_response(201, data)) as mock_req:
            result = cloud_client.set_build_status("abc", "SUCCESSFUL", "k", "https://ci.com")
        assert result == data
        url = mock_req.call_args.args[1]
        assert "/commit/abc/statuses/build" in url

    def test_set_build_status_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout setting build status"):
                dc_client.set_build_status("abc", "FAILED", "k", "https://ci.com")

    def test_set_build_status_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(403)):
            with pytest.raises(ValueError, match="Permission denied"):
                dc_client.set_build_status("abc", "FAILED", "k", "https://ci.com")


# ---------------------------------------------------------------------------
# Diff operations
# ---------------------------------------------------------------------------

class TestDiffOperations:
    def test_get_diff_dc(self, dc_client: BitbucketClient) -> None:
        data = {"diffs": []}
        with patch.object(dc_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = dc_client.get_diff("PROJ", "repo", "main", "feature")
        assert result == data
        url = mock_req.call_args.args[1]
        assert "compare/diff" in url
        assert "from=main" in url
        assert "to=feature" in url

    def test_get_diff_cloud(self, cloud_client: BitbucketClient) -> None:
        data = {"diffs": []}
        with patch.object(cloud_client, "_request", return_value=_mock_response(200, data)) as mock_req:
            result = cloud_client.get_diff("ignored", "repo", "main", "feature")
        assert result == data
        url = mock_req.call_args.args[1]
        assert "/diff/main..feature" in url

    def test_get_diff_timeout(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", side_effect=httpx.TimeoutException("t")):
            with pytest.raises(ValueError, match="Timeout getting diff"):
                dc_client.get_diff("PROJ", "repo", "a", "b")

    def test_get_diff_error(self, dc_client: BitbucketClient) -> None:
        with patch.object(dc_client, "_request", return_value=_mock_response(404)):
            with pytest.raises(ValueError, match="Resource not found"):
                dc_client.get_diff("PROJ", "repo", "a", "b")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_400_with_errors_json(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(400, json_data={"errors": [{"message": "field invalid"}]}, text='{"errors": []}')
        with pytest.raises(ValueError, match="Validation error: field invalid"):
            dc_client._handle_error(resp)

    def test_400_with_empty_errors(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(400, json_data={"errors": []}, text="bad")
        with pytest.raises(ValueError, match="Bad request: bad"):
            dc_client._handle_error(resp)

    def test_400_non_json(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(400, text="plain error")
        resp.json.side_effect = ValueError("not json")
        with pytest.raises(ValueError, match="Bad request: plain error"):
            dc_client._handle_error(resp)

    def test_401(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(401)
        with pytest.raises(ValueError, match="Authentication failed"):
            dc_client._handle_error(resp)

    def test_403(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(403)
        with pytest.raises(ValueError, match="Permission denied"):
            dc_client._handle_error(resp)

    def test_404(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(404)
        with pytest.raises(ValueError, match="Resource not found"):
            dc_client._handle_error(resp)

    def test_409(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(409, text="already exists")
        with pytest.raises(ValueError, match="Conflict: already exists"):
            dc_client._handle_error(resp)

    def test_429(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(429)
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            dc_client._handle_error(resp)

    def test_500(self, dc_client: BitbucketClient) -> None:
        resp = _mock_response(500, text="internal error")
        with pytest.raises(ValueError, match="Bitbucket API error \\(500\\): internal error"):
            dc_client._handle_error(resp)


# ---------------------------------------------------------------------------
# _request method
# ---------------------------------------------------------------------------

class TestRequestMethod:
    def test_request_uses_httpx_client(self, dc_client: BitbucketClient) -> None:
        mock_response = _mock_response(200)
        with patch("bitbucket_mcp_server.client.httpx.Client") as mock_cls:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.request.return_value = mock_response
            mock_cls.return_value = mock_ctx
            result = dc_client._request("GET", "https://example.com/api")
        assert result == mock_response
        mock_cls.assert_called_once_with(timeout=30, verify=True)


# ---------------------------------------------------------------------------
# Constructor edge cases
# ---------------------------------------------------------------------------

class TestClientConstructor:
    def test_none_auth_type_defaults_to_pat(self) -> None:
        cfg = _make_config(AuthType.PAT)
        cfg.auth_type = None
        client = BitbucketClient(cfg)
        assert client._auth_type == AuthType.PAT

    def test_verify_ssl_false(self) -> None:
        cfg = _make_config(AuthType.PAT)
        cfg.verify_ssl = False
        client = BitbucketClient(cfg)
        assert client.verify_ssl is False
