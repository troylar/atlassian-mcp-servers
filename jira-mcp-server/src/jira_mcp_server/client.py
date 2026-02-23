"""Jira REST API client with dual auth support (PAT + Cloud)."""

import base64
from typing import Any, Dict, List

import httpx

from jira_mcp_server.config import AuthType, JiraConfig
from jira_mcp_server.validators import _safe_error_text, validate_file_path


class JiraClient:
    """HTTP client for Jira REST API v2.

    Supports both Data Center (Bearer token) and Cloud (Basic auth) modes.
    """

    def __init__(self, config: JiraConfig):
        self.base_url = config.url
        self.timeout = config.timeout
        self._token = config.token
        self._email = config.email
        self._auth_type = config.auth_type or AuthType.PAT
        self.verify_ssl = config.verify_ssl

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
            raise ValueError("Authentication failed. Check your JIRA_MCP_TOKEN is valid and hasn't expired.")
        elif status == 403:
            raise ValueError("Permission denied. Your token doesn't have access to this resource.")
        elif status == 404:
            raise ValueError(f"Resource not found. The requested {self._get_resource_type(response)} does not exist.")
        elif status == 429:
            raise ValueError("Rate limit exceeded. Too many requests to Jira API. Please wait before retrying.")
        elif status == 400:
            try:
                error_data = response.json()
                errors = error_data.get("errors", {})
                messages = error_data.get("errorMessages", [])

                if errors:
                    error_str = ", ".join(f"{field}: {msg}" for field, msg in errors.items())
                    hint = self._disallowed_char_hint(errors, response)
                    msg = f"Validation error: {error_str}"
                    if hint:
                        msg += f" | Hint: {hint}"
                    raise ValueError(msg)
                elif messages:
                    raise ValueError(f"Validation error: {', '.join(messages)}")
            except (ValueError, KeyError) as e:
                if "Validation error" in str(e):
                    raise
                pass

            raise ValueError(f"Bad request: {_safe_error_text(response.text)}")
        else:
            raise ValueError(f"Jira API error ({status}): {_safe_error_text(response.text)}")

    @staticmethod
    def _disallowed_char_hint(errors: Dict[str, str], response: httpx.Response) -> str:
        """When Jira reports 'disallowed characters', identify suspicious chars in the request body."""
        all_msgs = " ".join(str(v) for v in errors.values())
        if "disallowed" not in all_msgs.lower():
            return ""
        try:
            body = response.request.content.decode("utf-8", errors="replace")
        except Exception:
            return ""
        suspicious: list[str] = []
        for ch in body:
            code = ord(ch)
            if code > 127 and ch not in '"\u00e9\u00e8\u00e0\u00f1\u00fc':
                name = f"U+{code:04X}"
                if name not in suspicious:
                    suspicious.append(name)
            if len(suspicious) >= 10:
                break
        if not suspicious:
            return "No obvious non-ASCII characters found in request. Check for wiki markup syntax issues."
        return f"Non-ASCII characters in request body: {', '.join(suspicious)}"

    def _get_resource_type(self, response: httpx.Response) -> str:
        url = str(response.request.url)
        if "/issue/" in url:
            return "issue"
        elif "/project/" in url or "/project" in url:
            return "project"
        elif "/filter/" in url:
            return "filter"
        elif "/board/" in url or "/board" in url:
            return "board"
        elif "/sprint/" in url or "/sprint" in url:
            return "sprint"
        elif "/user" in url:
            return "user"
        else:
            return "resource"

    def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
            response = client.request(method, url, headers=self._get_headers(), **kwargs)
            return response

    def health_check(self) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/serverInfo"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            server_info = response.json()
            return {
                "connected": True,
                "server_version": server_info.get("version", "unknown"),
                "base_url": server_info.get("baseUrl", self.base_url),
                "auth_type": self._auth_type.value,
            }
        except httpx.TimeoutException:
            raise ValueError(
                f"Connection timeout. Could not reach Jira at {self.base_url} within {self.timeout} seconds."
            )
        except httpx.NetworkError as e:
            raise ValueError(f"Network error connecting to Jira: {str(e)}")

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                if response.status_code == 404:
                    raise ValueError(f"Issue {issue_key} not found.")
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting issue {issue_key}")

    def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/issue"
        try:
            response = self._request("POST", url, json=issue_data)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating issue")

    def update_issue(self, issue_key: str, update_data: Dict[str, Any]) -> None:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        try:
            response = self._request("PUT", url, json=update_data)
            if response.status_code not in (200, 204):
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout updating issue {issue_key}")

    def delete_issue(self, issue_key: str, delete_subtasks: bool = False) -> None:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        params = {"deleteSubtasks": str(delete_subtasks).lower()}
        try:
            response = self._request("DELETE", url, params=params)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting issue {issue_key}")

    def link_issues(self, link_type: str, inward_issue: str, outward_issue: str) -> None:
        url = f"{self.base_url}/rest/api/2/issueLink"
        data = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_issue},
            "outwardIssue": {"key": outward_issue},
        }
        try:
            response = self._request("POST", url, json=data)
            if response.status_code not in (200, 201):
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError("Timeout linking issues")

    def get_project_schema(self, project_key: str, issue_type: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/2/issue/createmeta"
        params = {
            "projectKeys": project_key,
            "issuetypeNames": issue_type,
            "expand": "projects.issuetypes.fields",
        }
        try:
            response = self._request("GET", url, params=params)
            if response.status_code == 404:
                raise ValueError(
                    f"Project schema not found. Possible causes:\n"
                    f"  - Project '{project_key}' does not exist\n"
                    f"  - You don't have permission to access project '{project_key}'\n"
                    f"  - Issue type '{issue_type}' is not available in this project\n"
                    f"  - The createmeta endpoint may not be available in your Jira version\n"
                    f"Please verify the project key and issue type are correct."
                )
            elif response.status_code != 200:
                self._handle_error(response)
            data = response.json()
            projects = data.get("projects", [])
            if not projects:
                raise ValueError(
                    f"Project '{project_key}' returned no data. Possible causes:\n"
                    f"  - Project exists but you don't have permission to create issues\n"
                    f"  - Issue type '{issue_type}' is not available in this project\n"
                    f"Available projects: Check with your Jira administrator"
                )
            issue_types = projects[0].get("issuetypes", [])
            if not issue_types:
                raise ValueError(
                    f"Issue type '{issue_type}' not found in project '{project_key}'.\n"
                    f"Common issue types: Task, Bug, Story, Epic\n"
                    f"Note: Issue type names are case-sensitive"
                )
            fields = issue_types[0].get("fields", {})
            return [{"key": k, **v} for k, v in fields.items()]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting schema for {project_key}/{issue_type}")

    def search_issues(self, jql: str, max_results: int = 100, start_at: int = 0) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/search"
        data = {"jql": jql, "maxResults": max_results, "startAt": start_at}
        try:
            response = self._request("POST", url, json=data)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout executing search query")

    # Filter operations

    def create_filter(
        self, name: str, jql: str, description: str | None = None, favourite: bool = False
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/filter"
        data: Dict[str, Any] = {"name": name, "jql": jql, "favourite": favourite}
        if description:
            data["description"] = description
        try:
            response = self._request("POST", url, json=data)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating filter")

    def list_filters(self) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/filter/my"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing filters")

    def get_filter(self, filter_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/filter/{filter_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting filter {filter_id}")

    def update_filter(
        self,
        filter_id: str,
        name: str | None = None,
        jql: str | None = None,
        description: str | None = None,
        favourite: bool | None = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/filter/{filter_id}"
        data: Dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if jql is not None:
            data["jql"] = jql
        if description is not None:
            data["description"] = description
        if favourite is not None:
            data["favourite"] = favourite
        if not data:
            raise ValueError("At least one field must be provided to update")
        try:
            response = self._request("PUT", url, json=data)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout updating filter {filter_id}")

    def delete_filter(self, filter_id: str) -> None:
        url = f"{self.base_url}/rest/api/2/filter/{filter_id}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting filter {filter_id}")

    # Workflow operations

    def get_transitions(self, issue_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/transitions"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting transitions for {issue_key}")

    def transition_issue(self, issue_key: str, transition_id: str, fields: Dict[str, Any] | None = None) -> None:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/transitions"
        data: Dict[str, Any] = {"transition": {"id": transition_id}}
        if fields:
            data["fields"] = fields
        try:
            response = self._request("POST", url, json=data)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout transitioning issue {issue_key}")

    # Comment operations

    def add_comment(self, issue_key: str, body: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment"
        data = {"body": body}
        try:
            response = self._request("POST", url, json=data)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout adding comment to issue {issue_key}")

    def list_comments(self, issue_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout listing comments for issue {issue_key}")

    def update_comment(self, issue_key: str, comment_id: str, body: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment/{comment_id}"
        data = {"body": body}
        try:
            response = self._request("PUT", url, json=data)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout updating comment {comment_id} on issue {issue_key}")

    def delete_comment(self, issue_key: str, comment_id: str) -> None:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment/{comment_id}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting comment {comment_id} on issue {issue_key}")

    # Project operations

    def list_projects(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/2/project"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing projects")

    def get_project(self, project_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/project/{project_key}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting project {project_key}")

    def get_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/2/project/{project_key}/statuses"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting issue types for {project_key}")

    # Board operations (Agile API)

    def list_boards(self, project_key: str | None = None) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/agile/1.0/board"
        params: Dict[str, Any] = {}
        if project_key:
            params["projectKeyOrId"] = project_key
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing boards")

    def get_board(self, board_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/agile/1.0/board/{board_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting board {board_id}")

    # Sprint operations (Agile API)

    def list_sprints(self, board_id: str, state: str | None = None) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/agile/1.0/board/{board_id}/sprint"
        params: Dict[str, Any] = {}
        if state:
            params["state"] = state
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout listing sprints for board {board_id}")

    def get_sprint(self, sprint_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting sprint {sprint_id}")

    def get_sprint_issues(self, sprint_id: str, max_results: int = 50, start_at: int = 0) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
        params = {"maxResults": max_results, "startAt": start_at}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting issues for sprint {sprint_id}")

    # User operations

    def search_users(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/2/user/search"
        params = {"username": query, "maxResults": max_results}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout searching users")

    def get_user(self, username: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/user"
        params = {"username": username}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting user {username}")

    def get_myself(self) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/myself"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout getting current user")

    # Attachment operations

    def add_attachment(self, issue_key: str, file_path: str, filename: str | None = None) -> List[Dict[str, Any]]:
        safe_path = validate_file_path(file_path)
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/attachments"
        headers = self._get_headers()
        headers["X-Atlassian-Token"] = "no-check"
        del headers["Content-Type"]
        import os

        actual_filename = filename or os.path.basename(safe_path)
        try:
            with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
                with open(safe_path, "rb") as f:
                    response = client.post(
                        url,
                        headers=headers,
                        files={"file": (actual_filename, f)},
                    )
                    if response.status_code not in (200, 201):
                        self._handle_error(response)
                    return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout adding attachment to {issue_key}")
        except FileNotFoundError:  # pragma: no cover – validate_file_path catches first
            raise ValueError(f"File not found: {file_path}")

    def get_attachment(self, attachment_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/2/attachment/{attachment_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting attachment {attachment_id}")

    def delete_attachment(self, attachment_id: str) -> None:
        url = f"{self.base_url}/rest/api/2/attachment/{attachment_id}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting attachment {attachment_id}")

    # Priority and status operations

    def list_priorities(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/2/priority"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing priorities")

    def list_statuses(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/2/status"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing statuses")
