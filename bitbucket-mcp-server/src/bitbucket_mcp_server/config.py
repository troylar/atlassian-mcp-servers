"""Configuration management for Bitbucket MCP Server with dual auth support."""

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthType(str, Enum):
    PAT = "pat"
    CLOUD = "cloud"


class BitbucketConfig(BaseSettings):
    """Configuration for Bitbucket MCP Server.

    Self-hosted (Data Center) with PAT:
        BITBUCKET_MCP_URL=https://bitbucket.company.com
        BITBUCKET_MCP_TOKEN=<personal-access-token>

    Atlassian Cloud with email + API token:
        BITBUCKET_MCP_URL=https://bitbucket.org
        BITBUCKET_MCP_EMAIL=user@company.com
        BITBUCKET_MCP_TOKEN=<app-password>
        BITBUCKET_MCP_WORKSPACE=<workspace-slug>
    """

    url: str = Field(..., description="Bitbucket instance URL")
    token: str = Field(..., description="API authentication token or app password")
    email: Optional[str] = Field(default=None, description="Email for Cloud auth")
    auth_type: Optional[AuthType] = Field(default=None, description="Auth type: 'pat' or 'cloud'")
    workspace: Optional[str] = Field(default=None, description="Bitbucket Cloud workspace slug")
    timeout: int = Field(default=30, description="HTTP request timeout in seconds", gt=0)
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    model_config = SettingsConfigDict(
        env_prefix="BITBUCKET_MCP_",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("url")
    @classmethod
    def remove_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @model_validator(mode="after")
    def resolve_auth_type(self) -> "BitbucketConfig":
        if self.auth_type is None:
            if self.email:
                self.auth_type = AuthType.CLOUD
            else:
                self.auth_type = AuthType.PAT
        if self.auth_type == AuthType.CLOUD and not self.email:
            raise ValueError("BITBUCKET_MCP_EMAIL is required for Cloud authentication")
        return self
