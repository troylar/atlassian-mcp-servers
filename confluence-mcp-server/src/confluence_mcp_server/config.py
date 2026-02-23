"""Configuration management for Confluence MCP Server with dual auth support."""

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthType(str, Enum):
    PAT = "pat"
    CLOUD = "cloud"


class ConfluenceConfig(BaseSettings):
    """Configuration for Confluence MCP Server.

    Self-hosted (Data Center) with PAT:
        CONFLUENCE_MCP_URL=https://confluence.company.com
        CONFLUENCE_MCP_TOKEN=<personal-access-token>

    Atlassian Cloud with email + API token:
        CONFLUENCE_MCP_URL=https://company.atlassian.net
        CONFLUENCE_MCP_EMAIL=user@company.com
        CONFLUENCE_MCP_TOKEN=<api-token>
    """

    url: str = Field(..., description="Confluence instance URL")
    token: str = Field(..., description="API authentication token")
    email: Optional[str] = Field(default=None, description="Email for Atlassian Cloud auth")
    auth_type: Optional[AuthType] = Field(default=None, description="Auth type: 'pat' or 'cloud'")
    timeout: int = Field(default=30, description="HTTP request timeout in seconds", gt=0)
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    default_detail: str = Field(
        default="summary", description="Default response detail level: 'summary' or 'full'"
    )
    max_description_length: int = Field(
        default=500, description="Max description chars in summary mode. 0=no limit", ge=0
    )
    include_links: bool = Field(default=False, description="Include self/web URLs in responses")
    log_level: str = Field(default="WARNING", description="Log level: DEBUG, INFO, WARNING, or ERROR")

    model_config = SettingsConfigDict(
        env_prefix="CONFLUENCE_MCP_",
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
    def resolve_auth_type(self) -> "ConfluenceConfig":
        if self.auth_type is None:
            if self.email:
                self.auth_type = AuthType.CLOUD
            else:
                self.auth_type = AuthType.PAT
        if self.auth_type == AuthType.CLOUD and not self.email:
            raise ValueError("CONFLUENCE_MCP_EMAIL is required for Cloud authentication")
        return self
