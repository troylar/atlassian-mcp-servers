"""Configuration management for Jira MCP Server with dual auth support."""

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthType(str, Enum):
    """Authentication type for Jira API."""

    PAT = "pat"
    CLOUD = "cloud"


class JiraConfig(BaseSettings):
    """Configuration for Jira MCP Server loaded from environment variables.

    Supports two authentication modes:

    Self-hosted (Data Center) with PAT:
        JIRA_MCP_URL=https://jira.company.com
        JIRA_MCP_TOKEN=<personal-access-token>

    Atlassian Cloud with email + API token:
        JIRA_MCP_URL=https://company.atlassian.net
        JIRA_MCP_EMAIL=user@company.com
        JIRA_MCP_TOKEN=<api-token>

    Auto-detection: if EMAIL is set -> Cloud mode (Basic auth).
    If only TOKEN -> PAT mode (Bearer auth).
    Explicit AUTH_TYPE overrides auto-detection.
    """

    url: str = Field(..., description="Jira instance URL")
    token: str = Field(..., description="API authentication token")
    email: Optional[str] = Field(default=None, description="Email for Atlassian Cloud auth")
    auth_type: Optional[AuthType] = Field(default=None, description="Auth type: 'pat' or 'cloud'")
    cache_ttl: int = Field(default=3600, description="Schema cache TTL in seconds", gt=0)
    timeout: int = Field(default=30, description="HTTP request timeout in seconds", gt=0)
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    model_config = SettingsConfigDict(
        env_prefix="JIRA_MCP_",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("url")
    @classmethod
    def remove_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @model_validator(mode="after")
    def resolve_auth_type(self) -> "JiraConfig":
        if self.auth_type is None:
            if self.email:
                self.auth_type = AuthType.CLOUD
            else:
                self.auth_type = AuthType.PAT
        if self.auth_type == AuthType.CLOUD and not self.email:
            raise ValueError("JIRA_MCP_EMAIL is required for Cloud authentication")
        return self
