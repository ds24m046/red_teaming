import unittest
from pathlib import Path
from httpx import TransportError
from unittest.mock import MagicMock, patch

from red_teaming.gym.src.server.server import EddiServer
from red_teaming.gym.src.server.config import ServerConfig


class TestEddiServer(unittest.TestCase):

    def setUp(self):
        
        self.config = MagicMock(spec=ServerConfig)
        self.config.url = "http://localhost:7070"
        self.config.auth_token = "test-token"
        self.config.request_timeout_s = 10
        self.config.startup_timeout_s = 5
        self.config.compose_file = Path("docker-compose.yml")
        self.config.compose_project = "test-project"

        self.client_patcher = patch("red_teaming.gym.src.server.server.Client")
        self.mock_client_class = self.client_patcher.start()
        self.mock_client = self.mock_client_class.return_value

        self.addCleanup(self.client_patcher.stop)
        
        self.server = EddiServer(self.config)

    def test_initialization(self):
        
        self.mock_client_class.assert_called_once_with(
            base_url=self.config.url,
            timeout=self.config.request_timeout_s,
            headers={"Authorization": "Bearer test-token"},
        )

    def test_initialization_without_auth_token(self):
        
        self.config.auth_token = None
        server = EddiServer(self.config)

        self.mock_client_class.assert_called_with(
            base_url=self.config.url,
            timeout=self.config.request_timeout_s,
            headers={},
        )

    def test_client_property(self):
        self.assertIs(self.server.client, self.mock_client)

    @patch("red_teaming.gym.src.server.server.subprocess.run")
    def test_compose(self, mock_run):
        
        self.server._compose("up", "-d")

        mock_run.assert_called_once_with(
            [
                "docker", "compose",
                "--progress", "quiet",
                "-p", "test-project",
                "-f", "docker-compose.yml",
                "up", "-d",
            ],
            check=True,
        )

    @patch("red_teaming.gym.src.server.server.subprocess.run")
    def test_compose_without_compose_file(self, mock_run):
        
        self.config.compose_file = None

        with self.assertRaises(AssertionError):
            self.server._compose("up", "-d")

        mock_run.assert_not_called()

    @patch.object(EddiServer, "_wait_until_ready")
    @patch.object(EddiServer, "_compose")
    def test_start_with_compose(self, mock_compose, mock_wait):
        
        self.server.start()

        mock_compose.assert_called_once_with("up", "-d")
        mock_wait.assert_called_once()

    @patch.object(EddiServer, "_wait_until_ready")
    @patch.object(EddiServer, "_compose")
    def test_start_without_compose(self, mock_compose, mock_wait):
        
        self.config.compose_file = None
        self.server.start()

        mock_compose.assert_not_called()
        mock_wait.assert_called_once()
    
    @patch("red_teaming.gym.src.server.server.time.sleep")
    def test_wait_until_ready(self, mock_sleep):

        self.mock_client.get.return_value.status_code = 200
        self.server._wait_until_ready()

        self.mock_client.get.assert_called_once_with("/")
        mock_sleep.assert_not_called()

    @patch("red_teaming.gym.src.server.server.time.sleep")
    def test_wait_until_ready_retries_after_transport_error(self, mock_sleep):
        
        self.mock_client.get.side_effect = [
            TransportError("Connection refused"),
            MagicMock(status_code=200),
        ]
    
        self.server._wait_until_ready()

        self.assertEqual(self.mock_client.get.call_count, 2)
        mock_sleep.assert_called_once_with(2)

    @patch("red_teaming.gym.src.server.server.time.sleep")
    def test_wait_until_ready_accepts_client_errors(self, mock_sleep):
        
        self.mock_client.get.return_value.status_code = 404
        self.server._wait_until_ready()

        self.mock_client.get.assert_called_once_with("/")

    @patch("red_teaming.gym.src.server.server.time.sleep")
    @patch("red_teaming.gym.src.server.server.time.monotonic")
    def test_wait_until_ready_timeout(self, mock_monotonic, mock_sleep):
        
        mock_monotonic.side_effect = [0, 10]
        self.config.startup_timeout_s = 5

        with self.assertRaisesRegex(
            TimeoutError,
            "EDDI not reachable at http://localhost:7070",
        ):
            self.server._wait_until_ready()
    
    @patch("red_teaming.gym.src.server.server.subprocess.run")
    def test_destroy(self, mock_run):
        
        self.server.destroy()
        self.mock_client.close.assert_called_once()

        mock_run.assert_called_once_with(
            [
                "docker", "compose",
                "--progress", "quiet",
                "-p", "test-project",
                "-f", "docker-compose.yml",
                "down", "-v",
            ],
            check=True,
        )

    @patch("red_teaming.gym.src.server.server.subprocess.run")
    def test_destroy_without_compose(self, mock_run):
        
        self.config.compose_file = None
        self.server.destroy()

        self.mock_client.close.assert_called_once()
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
