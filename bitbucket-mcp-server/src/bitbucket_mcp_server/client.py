"""Bitbucket REST API client with dual auth support (PAT + Cloud)."""

import base64
from typing import Any, Dict, List, Optional

import httpx

from bitbucket_mcp_server.config import AuthType, BitbucketConfig


class BitbucketClient:
    """HTTP client for Bitbucket REST API.

    Cloud uses api.bitbucket.org/2.0/, Data Center uses /rest/api/1.0/.
    """

    def __init__(self, config: BitbucketConfig):
        self.base_url = config.url
        self.timeout = config.timeout
        self._token = config.token
        self._email = config.email
        self._auth_type = config.auth_type or AuthType.PAT
        self._workspace = config.workspace
        self.verify_ssl = config.verify_ssl

        if self._auth_type == AuthType.CLOUD:
            self._api_base = "https://api.bitbucket.org/2.0"
        else:
            self._api_base = f"{self.base_url}/rest/api/1.0"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._auth_type == AuthType.CLOUD:
            credentials = base64.b64encode(f"{self._email}:{self._token}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        else:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _handle_error(self, response: httpx.Response) -> None:
        status = response.status_code
        if status == 401:
            raise ValueError("Authentication failed. Check your BITBUCKET_MCP_TOKEN.")
        elif status == 403:
            raise ValueError("Permission denied.")
        elif status == 404:
            raise ValueError("Resource not found.")
        elif status == 409:
            raise ValueError(f"Conflict: {response.text[:200]}")
        elif status == 429:
            raise ValueError("Rate limit exceeded.")
        elif status == 400:
            try:
                error_data = response.json()
                errors = error_data.get("errors", [])
                if errors:
                    messages = [e.get("message", "") for e in errors]
                    raise ValueError(f"Validation error: {'; '.join(messages)}")
            except (ValueError, KeyError) as e:
                if "Validation error" in str(e):
                    raise
            raise ValueError(f"Bad request: {response.text[:200]}")
        else:
            raise ValueError(f"Bitbucket API error ({status}): {response.text[:200]}")

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
            return client.request(method, url, headers=self._get_headers(), **kwargs)

    def _dc_project_repo_url(self, project: str, repo: str) -> str:
        return f"{self._api_base}/projects/{project}/repos/{repo}"

    def _cloud_repo_url(self, repo_slug: str) -> str:
        return f"{self._api_base}/repositories/{self._workspace}/{repo_slug}"

    # Health check

    def health_check(self) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._api_base}/user"
        else:
            url = f"{self._api_base}/application-properties"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return {
                "connected": True,
                "base_url": self.base_url,
                "auth_type": self._auth_type.value,
            }
        except httpx.TimeoutException:
            raise ValueError(f"Connection timeout to Bitbucket at {self.base_url}")
        except httpx.NetworkError as e:
            raise ValueError(f"Network error connecting to Bitbucket: {str(e)}")

    # Project operations (Data Center)

    def list_projects(self, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        url = f"{self._api_base}/projects"
        params = {"limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing projects")

    def get_project(self, project_key: str) -> Dict[str, Any]:
        url = f"{self._api_base}/projects/{project_key}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting project {project_key}")

    def create_project(self, key: str, name: str, description: str = "") -> Dict[str, Any]:
        url = f"{self._api_base}/projects"
        payload: Dict[str, Any] = {"key": key, "name": name}
        if description:
            payload["description"] = description
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating project")

    # Repository operations

    def list_repos(self, project: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._api_base}/repositories/{self._workspace}"
            params: Dict[str, Any] = {"pagelen": limit, "page": (start // limit) + 1 if limit else 1}
        else:
            url = f"{self._api_base}/projects/{project}/repos"
            params = {"limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing repos")

    def get_repo(self, project: str, repo: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = self._cloud_repo_url(repo)
        else:
            url = self._dc_project_repo_url(project, repo)
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting repo {repo}")

    def create_repo(self, project: str, name: str, description: str = "") -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._api_base}/repositories/{self._workspace}/{name.lower()}"
            payload: Dict[str, Any] = {"scm": "git"}
            if description:
                payload["description"] = description
            method = "PUT"
        else:
            url = f"{self._api_base}/projects/{project}/repos"
            payload = {"name": name, "scmId": "git"}
            if description:
                payload["description"] = description
            method = "POST"
        try:
            response = self._request(method, url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating repo")

    def delete_repo(self, project: str, repo: str) -> None:
        if self._auth_type == AuthType.CLOUD:
            url = self._cloud_repo_url(repo)
        else:
            url = self._dc_project_repo_url(project, repo)
        try:
            response = self._request("DELETE", url)
            if response.status_code != 202 and response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting repo {repo}")

    def fork_repo(self, project: str, repo: str, name: str | None = None) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/forks"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/forks"
        payload: Dict[str, Any] = {}
        if name:
            payload["name"] = name
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout forking repo {repo}")

    # Branch operations

    def list_branches(self, project: str, repo: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/refs/branches"
            params: Dict[str, Any] = {"pagelen": limit}
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/branches"
            params = {"limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing branches")

    def create_branch(self, project: str, repo: str, name: str, start_point: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/refs/branches"
            payload = {"name": name, "target": {"hash": start_point}}
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/branches"
            payload = {"name": name, "startPoint": start_point}
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating branch")

    def delete_branch(self, project: str, repo: str, name: str) -> None:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/refs/branches/{name}"
            try:
                response = self._request("DELETE", url)
                if response.status_code != 204:
                    self._handle_error(response)
            except httpx.TimeoutException:
                raise ValueError(f"Timeout deleting branch {name}")
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/branches"
            payload = {"name": name, "dryRun": False}
            try:
                response = self._request("DELETE", url, json=payload)
                if response.status_code != 204:
                    self._handle_error(response)
            except httpx.TimeoutException:
                raise ValueError(f"Timeout deleting branch {name}")

    def get_default_branch(self, project: str, repo: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            repo_data = self.get_repo(project, repo)
            return {"name": repo_data.get("mainbranch", {}).get("name", "main")}
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/default-branch"
            try:
                response = self._request("GET", url)
                if response.status_code != 200:
                    self._handle_error(response)
                return response.json()  # type: ignore[no-any-return]
            except httpx.TimeoutException:
                raise ValueError("Timeout getting default branch")

    # Commit operations

    def list_commits(
        self, project: str, repo: str, branch: str | None = None, limit: int = 25, start: int = 0
    ) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/commits"
            params: Dict[str, Any] = {"pagelen": limit}
            if branch:
                params["include"] = branch
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/commits"
            params = {"limit": limit, "start": start}
            if branch:
                params["until"] = branch
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing commits")

    def get_commit(self, project: str, repo: str, commit_id: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/commit/{commit_id}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/commits/{commit_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting commit {commit_id}")

    def get_commit_diff(self, project: str, repo: str, commit_id: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/diff/{commit_id}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/commits/{commit_id}/diff"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting diff for commit {commit_id}")

    # Pull Request operations

    def list_prs(
        self, project: str, repo: str, state: str = "OPEN", limit: int = 25, start: int = 0
    ) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests"
            params: Dict[str, Any] = {"state": state.upper(), "pagelen": limit}
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests"
            params = {"state": state.upper(), "limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing PRs")

    def get_pr(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting PR {pr_id}")

    def create_pr(
        self,
        project: str,
        repo: str,
        title: str,
        source_branch: str,
        target_branch: str,
        description: str = "",
    ) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests"
            payload: Dict[str, Any] = {
                "title": title,
                "source": {"branch": {"name": source_branch}},
                "destination": {"branch": {"name": target_branch}},
            }
            if description:
                payload["description"] = description
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests"
            payload = {
                "title": title,
                "fromRef": {"id": f"refs/heads/{source_branch}"},
                "toRef": {"id": f"refs/heads/{target_branch}"},
            }
            if description:
                payload["description"] = description
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating PR")

    def update_pr(self, project: str, repo: str, pr_id: int, title: str | None = None,
                  description: str | None = None) -> Dict[str, Any]:
        pr = self.get_pr(project, repo, pr_id)
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}"
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if self._auth_type != AuthType.CLOUD:
            payload["version"] = pr.get("version", 0)
        try:
            response = self._request("PUT", url, json=payload)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout updating PR {pr_id}")

    def merge_pr(self, project: str, repo: str, pr_id: int, message: str = "") -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/merge"
            payload: Dict[str, Any] = {}
            if message:
                payload["message"] = message
        else:
            pr = self.get_pr(project, repo, pr_id)
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/merge"
            payload = {"version": pr.get("version", 0)}
            if message:
                payload["message"] = message
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout merging PR {pr_id}")

    def decline_pr(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/decline"
        else:
            pr = self.get_pr(project, repo, pr_id)
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/decline"
        try:
            response = self._request("POST", url, json={})
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout declining PR {pr_id}")

    def reopen_pr(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}"
            payload: Dict[str, Any] = {"state": "OPEN"}
            try:
                response = self._request("PUT", url, json=payload)
            except httpx.TimeoutException:
                raise ValueError(f"Timeout reopening PR {pr_id}")
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/reopen"
            try:
                response = self._request("POST", url, json={})
            except httpx.TimeoutException:
                raise ValueError(f"Timeout reopening PR {pr_id}")
        if response.status_code != 200:
            self._handle_error(response)
        return response.json()  # type: ignore[no-any-return]

    def get_pr_diff(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/diff"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/diff"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting PR {pr_id} diff")

    def get_pr_commits(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/commits"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/commits"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting PR {pr_id} commits")

    def get_pr_activities(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/activity"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/activities"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting PR {pr_id} activities")

    # PR Comment operations

    def add_pr_comment(self, project: str, repo: str, pr_id: int, text: str,
                       file_path: str | None = None, line: int | None = None) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/comments"
            payload: Dict[str, Any] = {"content": {"raw": text}}
            if file_path and line is not None:
                payload["inline"] = {"path": file_path, "to": line}
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/comments"
            payload = {"text": text}
            if file_path and line is not None:
                payload["anchor"] = {"path": file_path, "line": line, "lineType": "ADDED"}
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout adding comment to PR {pr_id}")

    def list_pr_comments(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/comments"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/comments"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout listing PR {pr_id} comments")

    def update_pr_comment(self, project: str, repo: str, pr_id: int,
                          comment_id: int, text: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/comments/{comment_id}"
            payload: Dict[str, Any] = {"content": {"raw": text}}
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/comments/{comment_id}"
            comment = self._request("GET", url).json()
            payload = {"text": text, "version": comment.get("version", 0)}
        try:
            response = self._request("PUT", url, json=payload)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout updating PR comment {comment_id}")

    def delete_pr_comment(self, project: str, repo: str, pr_id: int, comment_id: int) -> None:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/comments/{comment_id}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/comments/{comment_id}"
            comment = self._request("GET", url).json()
            url = f"{url}?version={comment.get('version', 0)}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting PR comment {comment_id}")

    # PR Review operations

    def approve_pr(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/approve"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/approve"
        try:
            response = self._request("POST", url, json={})
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout approving PR {pr_id}")

    def unapprove_pr(self, project: str, repo: str, pr_id: int) -> None:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/pullrequests/{pr_id}/approve"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/approve"
        try:
            response = self._request("DELETE", url)
            if response.status_code not in (200, 204):
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout unapproving PR {pr_id}")

    def needs_work_pr(self, project: str, repo: str, pr_id: int) -> Dict[str, Any]:
        url = f"{self._dc_project_repo_url(project, repo)}/pull-requests/{pr_id}/participants"
        payload = {"status": "NEEDS_WORK"}
        try:
            response = self._request("PUT", url, json=payload)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout marking PR {pr_id} needs work")

    # File operations

    def browse_files(self, project: str, repo: str, path: str = "", at: str | None = None) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/src"
            if at:
                url = f"{url}/{at}"
            if path:
                url = f"{url}/{path}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/browse/{path}"
        params: Dict[str, Any] = {}
        if at and self._auth_type != AuthType.CLOUD:
            params["at"] = at
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout browsing files at {path}")

    def get_file_content(self, project: str, repo: str, path: str, at: str | None = None) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/src"
            if at:
                url = f"{url}/{at}"
            url = f"{url}/{path}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/raw/{path}"
        params: Dict[str, Any] = {}
        if at and self._auth_type != AuthType.CLOUD:
            params["at"] = at
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                return response.json()  # type: ignore[no-any-return]
            return {"content": response.text, "path": path}
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting file {path}")

    # Tag operations

    def list_tags(self, project: str, repo: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/refs/tags"
            params: Dict[str, Any] = {"pagelen": limit}
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/tags"
            params = {"limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing tags")

    def create_tag(self, project: str, repo: str, name: str, target: str,
                   message: str = "") -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/refs/tags"
            payload: Dict[str, Any] = {"name": name, "target": {"hash": target}}
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/tags"
            payload = {"name": name, "startPoint": target, "message": message}
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating tag")

    def delete_tag(self, project: str, repo: str, name: str) -> None:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/refs/tags/{name}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/tags/{name}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting tag {name}")

    # Webhook operations

    def list_webhooks(self, project: str, repo: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/hooks"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/webhooks"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing webhooks")

    def create_webhook(self, project: str, repo: str, name: str, url_target: str,
                       events: List[str]) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            api_url = f"{self._cloud_repo_url(repo)}/hooks"
            payload: Dict[str, Any] = {
                "description": name,
                "url": url_target,
                "active": True,
                "events": events,
            }
        else:
            api_url = f"{self._dc_project_repo_url(project, repo)}/webhooks"
            payload = {
                "name": name,
                "url": url_target,
                "active": True,
                "events": events,
            }
        try:
            response = self._request("POST", api_url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating webhook")

    def delete_webhook(self, project: str, repo: str, webhook_id: str) -> None:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/hooks/{webhook_id}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/webhooks/{webhook_id}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting webhook {webhook_id}")

    # Build status operations

    def get_build_status(self, commit_id: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._api_base}/repositories/{self._workspace}/commit/{commit_id}/statuses"
        else:
            url = f"{self.base_url}/rest/build-status/1.0/commits/{commit_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting build status for {commit_id}")

    def set_build_status(self, commit_id: str, state: str, key: str, url_target: str,
                         description: str = "") -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            api_url = f"{self._api_base}/repositories/{self._workspace}/commit/{commit_id}/statuses/build"
        else:
            api_url = f"{self.base_url}/rest/build-status/1.0/commits/{commit_id}"
        payload: Dict[str, Any] = {
            "state": state,
            "key": key,
            "url": url_target,
        }
        if description:
            payload["description"] = description
        try:
            response = self._request("POST", api_url, json=payload)
            if response.status_code not in (200, 201, 204):
                self._handle_error(response)
            if response.status_code == 204:
                return {"success": True}
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout setting build status for {commit_id}")

    # Diff operations

    def get_diff(self, project: str, repo: str, from_ref: str, to_ref: str) -> Dict[str, Any]:
        if self._auth_type == AuthType.CLOUD:
            url = f"{self._cloud_repo_url(repo)}/diff/{from_ref}..{to_ref}"
        else:
            url = f"{self._dc_project_repo_url(project, repo)}/compare/diff"
            url = f"{url}?from={from_ref}&to={to_ref}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout getting diff")
