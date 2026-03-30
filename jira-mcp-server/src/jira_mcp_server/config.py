"""Configuration management for Jira MCP Server with multi-auth support."""

from enum import Enum
from typing import Optional

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthType(str, Enum):
    """Authentication type for Jira API."""

    PAT = "pat"
    CLOUD = "cloud"
    BASIC = "basic"


class JiraConfig(BaseSettings):
    """Configuration for Jira MCP Server loaded from environment variables.

    Supports three authentication modes:

    Self-hosted (Data Center) with PAT:
        JIRA_MCP_URL=https://jira.company.com
        JIRA_MCP_TOKEN=<personal-access-token>

    Atlassian Cloud with email + API token:
        JIRA_MCP_URL=https://company.atlassian.net
        JIRA_MCP_EMAIL=user@company.com
        JIRA_MCP_TOKEN=<api-token>

    Self-hosted (Data Center/Server) with username + password:
        JIRA_MCP_URL=https://jira.company.com
        JIRA_MCP_USERNAME=admin
        JIRA_MCP_PASSWORD=secret

    Auto-detection: if EMAIL is set -> Cloud mode (Basic auth with email:token).
    If USERNAME + PASSWORD -> Basic mode (Basic auth with username:password).
    If only TOKEN -> PAT mode (Bearer auth).
    Explicit AUTH_TYPE overrides auto-detection.
    """

    url: str = Field(..., description="Jira instance URL")
    token: Optional[str] = Field(default=None, description="API token (PAT/Cloud) or omit for Basic auth")
    email: Optional[str] = Field(default=None, description="Email for Atlassian Cloud auth")
    username: Optional[str] = Field(default=None, description="Username for Basic auth (Data Center/Server)")
    password: Optional[SecretStr] = Field(default=None, description="Password for Basic auth (Data Center/Server)")
    auth_type: Optional[AuthType] = Field(default=None, description="Auth type: 'pat', 'cloud', or 'basic'")
    cache_ttl: int = Field(default=3600, description="Schema cache TTL in seconds", gt=0)
    timeout: int = Field(default=30, description="HTTP request timeout in seconds", gt=0)
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    default_detail: str = Field(default="summary", description="Default response detail level: 'summary' or 'full'")
    max_description_length: int = Field(
        default=500, description="Max description chars in summary mode. 0=no limit", ge=0
    )
    default_limit: int = Field(default=25, description="Default pagination limit", gt=0)
    summary_fields: Optional[str] = Field(default=None, description="Comma-separated field override for summary mode")
    include_links: bool = Field(default=False, description="Include self/web URLs in responses")
    log_level: str = Field(default="WARNING", description="Log level: DEBUG, INFO, WARNING, or ERROR")

    model_config = SettingsConfigDict(
        env_prefix="JIRA_MCP_",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("url")
    @classmethod
    def remove_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        normalized = v.upper()
        if normalized not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValueError(f"Invalid log_level '{v}': must be DEBUG, INFO, WARNING, or ERROR")
        return normalized

    @model_validator(mode="after")
    def resolve_auth_type(self) -> "JiraConfig":
        if self.auth_type is None:
            if self.email:
                self.auth_type = AuthType.CLOUD
            elif self.username and self.password:
                self.auth_type = AuthType.BASIC
            else:
                self.auth_type = AuthType.PAT

        if self.auth_type == AuthType.CLOUD:
            if not self.email:
                raise ValueError("JIRA_MCP_EMAIL is required for Cloud authentication")
            if not self.token:
                raise ValueError("JIRA_MCP_TOKEN is required for Cloud authentication")
        elif self.auth_type == AuthType.BASIC:
            if not self.username:
                raise ValueError("JIRA_MCP_USERNAME is required for Basic authentication")
            if not self.password:
                raise ValueError("JIRA_MCP_PASSWORD is required for Basic authentication")
        elif self.auth_type == AuthType.PAT:
            if not self.token:
                raise ValueError("JIRA_MCP_TOKEN is required for PAT authentication")
        return self
