"""Confluence REST API client with dual auth support (PAT + Cloud)."""

import base64
import re
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape as xml_escape

import httpx

from confluence_mcp_server.config import AuthType, ConfluenceConfig


class ConfluenceClient:
    """HTTP client for Confluence REST API.

    Supports both Data Center (Bearer token) and Cloud (Basic auth) modes.
    Cloud uses /wiki/rest/api/, Data Center uses /rest/api/.
    """

    def __init__(self, config: ConfluenceConfig):
        self.base_url = config.url
        self.timeout = config.timeout
        self._token = config.token
        self._email = config.email
        self._auth_type = config.auth_type or AuthType.PAT
        self.verify_ssl = config.verify_ssl

        if self._auth_type == AuthType.CLOUD:
            self._api_base = f"{self.base_url}/wiki/rest/api"
        else:
            self._api_base = f"{self.base_url}/rest/api"

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
            raise ValueError("Authentication failed. Check your CONFLUENCE_MCP_TOKEN.")
        elif status == 403:
            raise ValueError("Permission denied.")
        elif status == 404:
            raise ValueError("Resource not found.")
        elif status == 429:
            raise ValueError("Rate limit exceeded.")
        elif status == 400:
            try:
                error_data = response.json()
                message = error_data.get("message", "")
                if message:
                    raise ValueError(f"Validation error: {message}")
            except (ValueError, KeyError) as e:
                if "Validation error" in str(e):
                    raise
            raise ValueError(f"Bad request: {response.text[:200]}")
        else:
            raise ValueError(f"Confluence API error ({status}): {response.text[:200]}")

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
            return client.request(method, url, headers=self._get_headers(), **kwargs)

    # Health check

    def health_check(self) -> Dict[str, Any]:
        url = f"{self._api_base}/settings/lookandfeel"
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
            raise ValueError(f"Connection timeout to Confluence at {self.base_url}")
        except httpx.NetworkError as e:
            raise ValueError(f"Network error connecting to Confluence: {str(e)}")

    # Page operations

    def get_page(self, page_id: str, expand: str = "body.storage,version,ancestors,space") -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}"
        params = {"expand": expand}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting page {page_id}")

    def get_page_by_title(self, space_key: str, title: str) -> Optional[Dict[str, Any]]:
        url = f"{self._api_base}/content"
        params = {
            "spaceKey": space_key,
            "title": title,
            "expand": "body.storage,version,space",
            "limit": 1,
        }
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            data = response.json()
            results = data.get("results", [])
            return results[0] if results else None
        except httpx.TimeoutException:
            raise ValueError(f"Timeout searching page by title in {space_key}")

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_id: str | None = None,
        representation: str = "storage",
    ) -> Dict[str, Any]:
        url = f"{self._api_base}/content"
        payload: Dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": body, "representation": representation}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": str(parent_id)}]
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating page")

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version: int,
        representation: str = "storage",
    ) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}"
        payload = {
            "id": page_id,
            "type": "page",
            "title": title,
            "body": {"storage": {"value": body, "representation": representation}},
            "version": {"number": version + 1},
        }
        try:
            response = self._request("PUT", url, json=payload)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout updating page {page_id}")

    def delete_page(self, page_id: str) -> None:
        url = f"{self._api_base}/content/{page_id}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting page {page_id}")

    def move_page(self, page_id: str, target_id: str, position: str = "append") -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/move/{position}/{target_id}"
        try:
            response = self._request("PUT", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout moving page {page_id}")

    def copy_page(self, page_id: str, destination_space: str, title: str | None = None) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/copy"
        payload: Dict[str, Any] = {
            "copyAttachments": True,
            "copyLabels": True,
            "destination": {"type": "space", "value": destination_space},
        }
        if title:
            payload["pageTitle"] = title
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout copying page {page_id}")

    def get_children(self, page_id: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/child/page"
        params = {"limit": limit, "start": start, "expand": "version,space"}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting children of page {page_id}")

    def get_ancestors(self, page_id: str) -> List[Dict[str, Any]]:
        page = self.get_page(page_id, expand="ancestors")
        return page.get("ancestors", [])  # type: ignore[no-any-return]

    def get_history(self, page_id: str) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/history"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting history of page {page_id}")

    def get_page_version(self, page_id: str, version: int) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/version/{version}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting version {version} of page {page_id}")

    def restore_page_version(self, page_id: str, version: int, message: str = "") -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/version"
        payload = {
            "operationKey": "restore",
            "params": {"versionNumber": version, "message": message},
        }
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout restoring version {version} of page {page_id}")

    # Search operations

    def search_cql(self, cql: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        url = f"{self._api_base}/content/search"
        params = {"cql": cql, "limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout executing CQL search")

    def search_content(
        self,
        query: str,
        space_key: str | None = None,
        content_type: str | None = None,
        limit: int = 25,
        start: int = 0,
    ) -> Dict[str, Any]:
        cql_parts = [f'text ~ "{query}"']
        if space_key:
            cql_parts.append(f'space = "{space_key}"')
        if content_type:
            cql_parts.append(f'type = "{content_type}"')
        cql = " AND ".join(cql_parts)
        return self.search_cql(cql=cql, limit=limit, start=start)

    # Space operations

    def list_spaces(self, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        url = f"{self._api_base}/space"
        params = {"limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing spaces")

    def get_space(self, space_key: str) -> Dict[str, Any]:
        url = f"{self._api_base}/space/{space_key}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting space {space_key}")

    def create_space(self, key: str, name: str, description: str = "") -> Dict[str, Any]:
        url = f"{self._api_base}/space"
        payload: Dict[str, Any] = {
            "key": key,
            "name": name,
        }
        if description:
            payload["description"] = {"plain": {"value": description, "representation": "plain"}}
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating space")

    # Comment operations

    def add_comment(self, page_id: str, body: str, representation: str = "storage") -> Dict[str, Any]:
        url = f"{self._api_base}/content"
        payload = {
            "type": "comment",
            "container": {"id": page_id, "type": "page"},
            "body": {"storage": {"value": body, "representation": representation}},
        }
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout adding comment to page {page_id}")

    def list_comments(self, page_id: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/child/comment"
        params = {"limit": limit, "start": start, "expand": "body.storage"}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout listing comments for page {page_id}")

    def update_comment(self, comment_id: str, body: str, version: int) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{comment_id}"
        payload = {
            "type": "comment",
            "body": {"storage": {"value": body, "representation": "storage"}},
            "version": {"number": version + 1},
        }
        try:
            response = self._request("PUT", url, json=payload)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout updating comment {comment_id}")

    def delete_comment(self, comment_id: str) -> None:
        url = f"{self._api_base}/content/{comment_id}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting comment {comment_id}")

    # Attachment operations

    def add_attachment(self, page_id: str, file_path: str, filename: str | None = None) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/child/attachment"
        headers = self._get_headers()
        headers["X-Atlassian-Token"] = "nocheck"
        del headers["Content-Type"]
        import os

        actual_filename = filename or os.path.basename(file_path)
        try:
            with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
                with open(file_path, "rb") as f:
                    response = client.post(url, headers=headers, files={"file": (actual_filename, f)})
                    if response.status_code not in (200, 201):
                        self._handle_error(response)
                    return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout adding attachment to page {page_id}")
        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}")

    def list_attachments(self, page_id: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/child/attachment"
        params = {"limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout listing attachments for page {page_id}")

    def get_attachment(self, attachment_id: str) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{attachment_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting attachment {attachment_id}")

    def delete_attachment(self, attachment_id: str) -> None:
        url = f"{self._api_base}/content/{attachment_id}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting attachment {attachment_id}")

    # Label operations

    def add_label(self, page_id: str, label: str) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/label"
        payload = [{"prefix": "global", "name": label}]
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout adding label to page {page_id}")

    def remove_label(self, page_id: str, label: str) -> None:
        url = f"{self._api_base}/content/{page_id}/label/{label}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout removing label from page {page_id}")

    def get_labels(self, page_id: str) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/label"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting labels for page {page_id}")

    # Content conversion

    def convert_content(self, value: str, from_repr: str, to_repr: str) -> Dict[str, Any]:
        url = f"{self._api_base}/contentbody/convert/{to_repr}"
        payload = {"value": value, "representation": from_repr}
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout converting content")

    # User operations

    def get_user(self, account_id: str) -> Dict[str, Any]:
        url = f"{self._api_base}/user"
        params = {"accountId": account_id}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting user {account_id}")

    def get_current_user(self) -> Dict[str, Any]:
        url = f"{self._api_base}/user/current"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout getting current user")

    # Blog operations

    def create_blog(self, space_key: str, title: str, body: str) -> Dict[str, Any]:
        url = f"{self._api_base}/content"
        payload = {
            "type": "blogpost",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }
        try:
            response = self._request("POST", url, json=payload)
            if response.status_code not in (200, 201):
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout creating blog post")

    def list_blogs(self, space_key: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        url = f"{self._api_base}/content"
        params = {"type": "blogpost", "spaceKey": space_key, "limit": limit, "start": start}
        try:
            response = self._request("GET", url, params=params)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError("Timeout listing blog posts")

    def get_blog(self, blog_id: str) -> Dict[str, Any]:
        return self.get_page(blog_id)

    def delete_blog(self, blog_id: str) -> None:
        url = f"{self._api_base}/content/{blog_id}"
        try:
            response = self._request("DELETE", url)
            if response.status_code != 204:
                self._handle_error(response)
        except httpx.TimeoutException:
            raise ValueError(f"Timeout deleting blog {blog_id}")

    def update_blog(self, blog_id: str, title: str, body: str, version: int) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{blog_id}"
        payload = {
            "type": "blogpost",
            "title": title,
            "body": {"storage": {"value": body, "representation": "storage"}},
            "version": {"number": version + 1},
        }
        try:
            response = self._request("PUT", url, json=payload)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout updating blog {blog_id}")

    # Permission operations

    def get_page_permissions(self, page_id: str) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/restriction"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout getting permissions for page {page_id}")

    def set_page_permissions(self, page_id: str, restrictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = f"{self._api_base}/content/{page_id}/restriction"
        try:
            response = self._request("PUT", url, json=restrictions)
            if response.status_code != 200:
                self._handle_error(response)
            return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException:
            raise ValueError(f"Timeout setting permissions for page {page_id}")

    # Macro rendering

    _MACRO_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    _VALID_BODY_TYPES = frozenset({"plain-text-body", "rich-text-body"})

    def render_macro(
        self,
        macro_name: str,
        parameters: Dict[str, str] | None = None,
        body: str | None = None,
        body_type: str = "rich-text-body",
    ) -> Dict[str, str]:
        """Render a Confluence macro as storage-format XHTML.

        Pure string generation — no API calls. The returned XHTML can be
        embedded in page body content passed to create_page/update_page.

        Args:
            macro_name: The macro identifier (e.g. "code", "toc", "panel",
                        "info", "warning", "expand", or any plugin macro name).
            parameters: Optional dict of macro parameters.
            body: Optional macro body content.
            body_type: How to wrap the body — "plain-text-body" (CDATA-wrapped,
                       for code/noformat) or "rich-text-body" (XHTML content,
                       for panel/expand/info). Default: "rich-text-body".
                       Note: with "rich-text-body", the body is included as-is
                       (no escaping). Caller must ensure body is trusted XHTML.

        Returns:
            Dict with "xhtml" (the rendered macro markup) and "macro_name".
        """
        if not macro_name or not macro_name.strip():
            raise ValueError("macro_name must not be empty")
        macro_name = macro_name.strip()
        if not self._MACRO_NAME_RE.match(macro_name):
            raise ValueError(
                f"Invalid macro_name '{macro_name}': must start with a letter "
                "and contain only letters, digits, hyphens, and underscores"
            )
        if body_type not in self._VALID_BODY_TYPES:
            raise ValueError(
                f"Invalid body_type '{body_type}': must be one of "
                f"{sorted(self._VALID_BODY_TYPES)}"
            )

        parts: list[str] = [f'<ac:structured-macro ac:name="{xml_escape(macro_name)}">']

        if parameters:
            for key, value in parameters.items():
                escaped_key = xml_escape(str(key))
                escaped_value = xml_escape(str(value))
                parts.append(f'<ac:parameter ac:name="{escaped_key}">{escaped_value}</ac:parameter>')

        if body:
            if body_type == "plain-text-body":
                safe_body = body.replace("]]>", "]]]]><![CDATA[>")
                parts.append(f"<ac:plain-text-body><![CDATA[{safe_body}]]></ac:plain-text-body>")
            else:
                parts.append(f"<ac:rich-text-body>{body}</ac:rich-text-body>")

        parts.append("</ac:structured-macro>")
        xhtml = "".join(parts)

        return {"xhtml": xhtml, "macro_name": macro_name}
