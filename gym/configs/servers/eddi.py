from pathlib import Path
from pydantic import Field

from red_teaming.gym.base import BaseConfig


class EddiServerConfig(BaseConfig):
    url: str = "http://localhost:7070"
    startup_timeout_s: int = Field(default=120, gt=0)
    request_timeout_s: int = Field(default=60, gt=0)
    auth_token: str | None = None
    compose_file: Path | None = None
    compose_project: str = "skybook-gym"
