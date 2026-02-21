"""Pydantic models for Confluence MCP Server."""

from typing import List, Optional


class ConfluenceAPIError(Exception):
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        self.errors = errors or []
        super().__init__(message)
