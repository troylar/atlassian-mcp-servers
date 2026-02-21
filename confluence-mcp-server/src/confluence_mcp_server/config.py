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

    model_config = SettingsConfigDict(
        env_prefix="CONFLUENCE_MCP_",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("url")
    @classmethod
    def remove_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

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
