"""Tests for response formatters."""

from unittest.mock import MagicMock

import pytest

from bitbucket_mcp_server.formatters import (
    _extract_name,
    _links,
    _max_desc,
    _resolve_detail,
    format_branch,
    format_branches,
    format_commit,
    format_commits,
    format_pr,
    format_pr_comment,
    format_pr_comments,
    format_project,
    format_projects,
    format_prs,
    format_repo,
    format_repos,
    format_tag,
    format_tags,
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
        assert _max_desc(_make_config(max_description_length=200)) == 200

    def test_without_config(self) -> None:
        assert _max_desc(None) == 500


class TestLinks:
    def test_with_config_true(self) -> None:
        assert _links(_make_config(include_links=True)) is True

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
        assert truncate_text("x" * 10000, 0) == "x" * 10000


class TestExtractName:
    def test_none(self) -> None:
        assert _extract_name(None) is None

    def test_dict_display_name(self) -> None:
        assert _extract_name({"displayName": "Alice"}) == "Alice"

    def test_dict_display_name_snake(self) -> None:
        assert _extract_name({"display_name": "Bob"}) == "Bob"

    def test_dict_name(self) -> None:
        assert _extract_name({"name": "dev"}) == "dev"

    def test_string(self) -> None:
        assert _extract_name("raw") == "raw"


class TestFormatProject:
    def test_basic(self) -> None:
        raw = {"key": "PROJ", "name": "My Project", "description": "A project"}
        result = format_project(raw, _make_config())
        assert result["key"] == "PROJ"
        assert result["name"] == "My Project"
        assert result["description"] == "A project"
        assert "self" not in result

    def test_with_links(self) -> None:
        raw = {
            "key": "P",
            "name": "N",
            "links": {"self": [{"href": "http://bb/projects/P"}]},
        }
        result = format_project(raw, _make_config(include_links=True))
        assert result["self"] == "http://bb/projects/P"

    def test_with_links_empty(self) -> None:
        raw = {"key": "P", "name": "N", "links": {"self": []}}
        result = format_project(raw, _make_config(include_links=True))
        assert "self" not in result

    def test_no_links_key(self) -> None:
        raw = {"key": "P", "name": "N"}
        result = format_project(raw, _make_config(include_links=True))
        assert "self" not in result


class TestFormatProjects:
    def test_basic(self) -> None:
        raw = {"values": [{"key": "A"}, {"key": "B"}], "size": 2, "start": 0, "limit": 25}
        result = format_projects(raw, _make_config())
        assert result["size"] == 2
        assert len(result["values"]) == 2

    def test_empty(self) -> None:
        result = format_projects({"values": []}, None)
        assert result["size"] == 0


class TestFormatRepo:
    def test_basic(self) -> None:
        raw = {
            "slug": "my-repo",
            "name": "My Repo",
            "description": "A repo",
            "project": {"key": "PROJ"},
        }
        result = format_repo(raw, _make_config())
        assert result["slug"] == "my-repo"
        assert result["project"] == "PROJ"
        assert "cloneUrl" not in result

    def test_with_links(self) -> None:
        raw = {
            "slug": "r",
            "name": "R",
            "links": {"clone": [{"name": "http", "href": "http://bb/r.git"}, {"name": "ssh", "href": "ssh://bb/r"}]},
        }
        result = format_repo(raw, _make_config(include_links=True))
        assert result["cloneUrl"] == "http://bb/r.git"

    def test_no_project(self) -> None:
        raw = {"slug": "r", "name": "R"}
        result = format_repo(raw, None)
        assert "project" not in result

    def test_with_links_no_http_clone(self) -> None:
        raw = {
            "slug": "r",
            "name": "R",
            "links": {"clone": [{"name": "ssh", "href": "ssh://bb/r"}]},
        }
        result = format_repo(raw, _make_config(include_links=True))
        assert "cloneUrl" not in result


class TestFormatRepos:
    def test_basic(self) -> None:
        raw = {"values": [{"slug": "a"}], "size": 1, "start": 0, "limit": 25}
        result = format_repos(raw, _make_config())
        assert result["size"] == 1


class TestFormatBranch:
    def test_dc_branch(self) -> None:
        raw = {"displayId": "main", "latestCommit": "abc123", "isDefault": True}
        result = format_branch(raw, _make_config())
        assert result["displayId"] == "main"
        assert result["latestCommit"] == "abc123"
        assert result["isDefault"] is True

    def test_cloud_branch(self) -> None:
        raw = {"name": "feature", "target": {"hash": "def456"}}
        result = format_branch(raw, None)
        assert result["displayId"] == "feature"
        assert result["latestCommit"] == "def456"

    def test_fallback_changeset(self) -> None:
        raw = {"displayId": "dev", "latestChangeset": "aaa"}
        result = format_branch(raw, None)
        assert result["latestCommit"] == "aaa"


class TestFormatBranches:
    def test_basic(self) -> None:
        raw = {"values": [{"displayId": "main"}], "size": 1, "start": 0, "limit": 25}
        result = format_branches(raw, _make_config())
        assert result["size"] == 1


class TestFormatCommit:
    def test_dc_commit(self) -> None:
        raw = {
            "id": "abc123",
            "displayId": "abc123",
            "message": "fix bug",
            "author": {"name": "Alice"},
            "authorTimestamp": 1700000000,
        }
        result = format_commit(raw, _make_config())
        assert result["id"] == "abc123"
        assert result["message"] == "fix bug"
        assert result["author"] == "Alice"

    def test_cloud_commit(self) -> None:
        raw = {"hash": "def456", "message": "add feature", "date": "2024-01-01"}
        result = format_commit(raw, None)
        assert result["id"] == "def456"
        assert result["authorTimestamp"] == "2024-01-01"

    def test_with_links(self) -> None:
        raw = {"id": "abc", "links": {"self": [{"href": "http://bb/commits/abc"}]}}
        result = format_commit(raw, _make_config(include_links=True))
        assert result["self"] == "http://bb/commits/abc"

    def test_truncated_message(self) -> None:
        raw = {"id": "x", "message": "a" * 600}
        result = format_commit(raw, _make_config(max_description_length=100))
        assert len(result["message"]) == 103


class TestFormatCommits:
    def test_basic(self) -> None:
        raw = {"values": [{"id": "a"}], "size": 1, "start": 0, "limit": 25}
        result = format_commits(raw, _make_config())
        assert result["size"] == 1


class TestFormatPR:
    def test_dc_pr(self) -> None:
        raw = {
            "id": 1,
            "title": "Fix bug",
            "description": "Fixes #123",
            "state": "OPEN",
            "author": {"user": {"displayName": "Alice"}},
            "fromRef": {"displayId": "feature"},
            "toRef": {"displayId": "main"},
            "reviewers": [{"user": {"displayName": "Bob"}}],
        }
        result = format_pr(raw, _make_config())
        assert result["id"] == 1
        assert result["title"] == "Fix bug"
        assert result["author"] == "Alice"
        assert result["sourceBranch"] == "feature"
        assert result["targetBranch"] == "main"
        assert result["reviewers"] == ["Bob"]

    def test_cloud_pr(self) -> None:
        raw = {
            "id": 2,
            "title": "Add feature",
            "state": "OPEN",
            "source": {"branch": {"name": "feat"}},
            "destination": {"branch": {"name": "main"}},
            "author": {"user": {"display_name": "Carol"}},
        }
        result = format_pr(raw, None)
        assert result["sourceBranch"] == "feat"
        assert result["targetBranch"] == "main"

    def test_with_links(self) -> None:
        raw = {"id": 1, "title": "T", "state": "OPEN", "links": {"self": [{"href": "http://bb/pr/1"}]}}
        result = format_pr(raw, _make_config(include_links=True))
        assert result["self"] == "http://bb/pr/1"

    def test_no_refs(self) -> None:
        raw = {"id": 1, "title": "T", "state": "OPEN"}
        result = format_pr(raw, None)
        assert "sourceBranch" not in result
        assert "targetBranch" not in result

    def test_no_author(self) -> None:
        raw = {"id": 1, "title": "T", "state": "OPEN", "author": "string_author"}
        result = format_pr(raw, None)
        assert result["author"] is None


class TestFormatPRs:
    def test_basic(self) -> None:
        raw = {"values": [{"id": 1, "title": "T", "state": "OPEN"}], "size": 1, "start": 0, "limit": 25}
        result = format_prs(raw, _make_config())
        assert result["size"] == 1


class TestFormatPRComment:
    def test_dc_comment(self) -> None:
        raw = {
            "id": 10,
            "text": "Looks good!",
            "author": {"displayName": "Bob"},
            "createdDate": 1700000000,
        }
        result = format_pr_comment(raw, _make_config())
        assert result["id"] == 10
        assert result["text"] == "Looks good!"
        assert result["author"] == "Bob"

    def test_cloud_comment(self) -> None:
        raw = {
            "id": 20,
            "content": {"raw": "Nice work"},
            "created_on": "2024-01-01",
        }
        result = format_pr_comment(raw, None)
        assert result["text"] == "Nice work"
        assert result["createdDate"] == "2024-01-01"


class TestFormatPRComments:
    def test_basic(self) -> None:
        raw = {"values": [{"id": 1, "text": "hi"}], "size": 1, "start": 0, "limit": 25}
        result = format_pr_comments(raw, _make_config())
        assert result["size"] == 1


class TestFormatTag:
    def test_dc_tag(self) -> None:
        raw = {"displayId": "v1.0", "hash": "abc123", "message": "Release 1.0"}
        result = format_tag(raw, _make_config())
        assert result["displayId"] == "v1.0"
        assert result["hash"] == "abc123"
        assert result["message"] == "Release 1.0"

    def test_cloud_tag(self) -> None:
        raw = {"name": "v2.0", "latestCommit": "def456"}
        result = format_tag(raw, None)
        assert result["displayId"] == "v2.0"
        assert result["hash"] == "def456"


class TestFormatTags:
    def test_basic(self) -> None:
        raw = {"values": [{"displayId": "v1"}], "size": 1, "start": 0, "limit": 25}
        result = format_tags(raw, _make_config())
        assert result["size"] == 1
        assert len(result["values"]) == 1
