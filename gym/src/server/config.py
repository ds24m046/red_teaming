from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict


class ServerConfig(BaseModel):
    """How to reach the local EDDI server."""
    
    model_config = ConfigDict(extra="forbid")

    url: str = "http://localhost:7070"
    startup_timeout_s: int = Field(default=120, gt=0)
    request_timeout_s: int = Field(default=60, gt=0)
    auth_token: str | None = None
    compose_file: Path | None = None
    compose_project: str = "skybook-gym"