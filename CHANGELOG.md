# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Version numbers follow `<server>-v<major>.<minor>.<patch>`.

## Jira MCP Server

### [2.2.0] - 2025-10-25

#### Added
- Text sanitization utilities for Jira wiki format conversion

### [2.1.0] - 2025-10-24

#### Added
- `jira_priority_list_tool` — list all available Jira priorities
- `jira_status_list_tool` — list all available Jira statuses

### [2.0.0] - 2025-10-24

#### Added
- Dual auth support (Cloud Basic + Data Center PAT) with auto-detection
- 37 tools: issues, search, filters, workflow, comments, projects, boards, sprints, users, attachments
- FastMCP 3.x integration

## Confluence MCP Server

### [1.1.0] - 2025-10-25

#### Added
- `confluence_content_from_markdown` — markdown to Confluence storage format (XHTML) converter using mistune
- `mistune>=3.0.0` dependency

### [1.0.0] - 2025-10-24

#### Added
- Initial release with 39 tools
- Dual auth support (Cloud Basic + Data Center PAT) with auto-detection
- Pages, search, spaces, comments, attachments, labels, content conversion, users, blog, permissions, macro rendering

## Bitbucket MCP Server

### [1.0.0] - 2025-10-24

#### Added
- Initial release with 44 tools
- Dual auth support (Cloud Basic + Data Center PAT) with auto-detection
- Projects, repos, branches, commits, PRs, PR comments, PR reviews, files, tags, webhooks, build status, diffs
