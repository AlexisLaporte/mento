"""Project configuration dataclass — hydrated from DB."""

from dataclasses import dataclass, field


@dataclass
class ProjectConfig:
    slug: str = ""
    title: str = "Mento"
    repo_full_name: str = ""
    installation_id: int = 0
    docs_paths: list[str] = field(default_factory=lambda: ["docs"])
    allowed_files: list[str] = field(default_factory=list)

    owner_email: str = ""
    color: str = "#6366F1"
    custom_domain: str = ""
    default_branch: str = "main"
    is_public: bool = False
