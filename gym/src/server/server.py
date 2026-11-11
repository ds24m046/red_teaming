import time
import subprocess
from httpx import Client, TransportError

from red_teaming.gym.src.server.config import ServerConfig


class EddiServer:

    def __init__(self, config: ServerConfig) -> None:
    
        headers = {"Authorization": f"Bearer {config.auth_token}"} if config.auth_token else {}
        
        self._config = config
        self._client = Client(base_url=config.url, timeout=config.request_timeout_s, headers=headers)

    @property
    def client(self) -> Client:
        
        return self._client

    def _compose(self, *args: str) -> None:
        
        assert self._config.compose_file is not None
        assert self._config.compose_project is not None
        
        subprocess.run(
            [
                "docker", "compose",
                "--progress", "quiet",
                "-p", self._config.compose_project,
                "-f", str(self._config.compose_file),
                *args,
            ],
            check=True,
        )

    def start(self) -> None:
        
        if self._config.compose_file is not None:
            self._compose("up", "-d")
        
        self._wait_until_ready()

    def _wait_until_ready(self) -> None:
        
        deadline = time.monotonic() + self._config.startup_timeout_s
        
        while time.monotonic() < deadline:
        
            try:
                if self._client.get("/").status_code < 500:
                    return
            except TransportError:
                pass
            
            time.sleep(2)
        
        raise TimeoutError(f"EDDI not reachable at {self._config.url}")

    def destroy(self) -> None:
        
        self._client.close()
        
        if self._config.compose_file is not None:
            self._compose("down", "-v")
