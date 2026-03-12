"""YAML config loader for Memento instances."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class GithubConfig:
    repo: str = ""
    token_env: str = "GITHUB_TOKEN"


@dataclass
class AuthConfig:
    allowed_domains: list[str] = field(default_factory=list)
    allowed_emails: list[str] = field(default_factory=list)
    initial_admin: str = ""


@dataclass
class BrandingConfig:
    color: str = "#6366F1"
    title: str = "Memento"


@dataclass
class Config:
    name: str = "Memento"
    base_path: str = "."
    docs_paths: list[str] = field(default_factory=lambda: ["docs"])
    allowed_files: list[str] = field(default_factory=list)
    github: GithubConfig = field(default_factory=GithubConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    branding: BrandingConfig = field(default_factory=BrandingConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        github = GithubConfig(**data.pop("github", {}))
        auth = AuthConfig(**data.pop("auth", {}))
        branding = BrandingConfig(**data.pop("branding", {}))
        return cls(github=github, auth=auth, branding=branding, **data)
