"""Pydantic models for Jira MCP Server."""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    USER = "user"
    OPTION = "option"
    ARRAY = "array"
    MULTI_SELECT = "multiselect"


class FieldSchema(BaseModel):
    key: str = Field(..., description="Field identifier")
    name: str = Field(..., description="Human-readable field name")
    type: FieldType = Field(..., description="Field data type")
    required: bool = Field(..., description="Whether field is mandatory")
    allowed_values: Optional[List[str]] = Field(default=None, description="Allowed values for select fields")
    custom: bool = Field(..., description="Whether this is a custom field")
    schema_type: Optional[str] = Field(default=None, description="Jira schema type details")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not (v.isidentifier() or v.startswith("customfield_")):
            raise ValueError(f"Invalid field key: {v}")
        return v


class Issue(BaseModel):
    key: str = Field(..., pattern=r"^[A-Z]+-\d+$")
    id: str
    self: str
    project: str
    issue_type: str
    summary: str = Field(..., min_length=1)
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created: datetime
    updated: datetime
    due_date: Optional[date] = None
    labels: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class Project(BaseModel):
    key: str = Field(..., pattern=r"^[A-Z][A-Z0-9]{1,9}$")
    id: str
    name: str
    self: str
    issue_types: List[str]
    lead: Optional[str] = None


class SearchResult(BaseModel):
    total: int
    max_results: int
    start_at: int
    issues: List[Issue]


class CachedSchema(BaseModel):
    project_key: str
    issue_type: str
    fields: List[FieldSchema]
    cached_at: datetime
    expires_at: datetime


class Filter(BaseModel):
    id: str
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    jql: str = Field(..., min_length=1)
    owner: str
    favourite: bool = False
    share_permissions: List[str] = Field(default_factory=list)


class WorkflowTransition(BaseModel):
    id: str
    name: str
    to_status: str
    has_screen: bool
    required_fields: List[str] = Field(default_factory=list)


class Comment(BaseModel):
    id: str
    author: str
    body: str = Field(..., min_length=1)
    created: datetime
    updated: datetime
    visibility: Optional[str] = None


class JiraAPIError(Exception):
    def __init__(self, message: str, jira_errors: Optional[List[str]] = None):
        self.jira_errors = jira_errors or []
        super().__init__(message)


class FieldValidationError(Exception):
    def __init__(self, field_name: str, reason: str):
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"Field '{field_name}' validation failed: {reason}")
