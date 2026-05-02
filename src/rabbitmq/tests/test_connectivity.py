import unittest
from typing import Any
from unittest.mock import patch

from src.rabbitmq.rabbitmq_api import RabbitMQClient


class TestRabbitMQClientConnectivity(unittest.TestCase):
    def test_client_defaults_to_http(self) -> None:
        client = RabbitMQClient(host="localhost", port=15672)
        self.assertEqual(client.base_url, "http://localhost:15672/api")

    def test_client_supports_https(self) -> None:
        client = RabbitMQClient(host="remote-host", port=15671, use_ssl=True)
        self.assertEqual(client.base_url, "https://remote-host:15671/api")

    @patch("urllib.request.urlopen")
    def test_test_connection_logic(self, mock_urlopen: Any) -> None:
        # Mocking /api/whoami and /api/overview
        import json
        from unittest.mock import MagicMock

        # whoami response
        res1 = MagicMock()
        res1.__enter__.return_value = res1
        res1.read.return_value = json.dumps(
            {"name": "guest", "tags": ["administrator"]}
        ).encode()
        res1.status = 200

        # overview response
        res2 = MagicMock()
        res2.__enter__.return_value = res2
        res2.read.return_value = json.dumps({"rabbitmq_version": "3.13.0"}).encode()
        res2.status = 200

        mock_urlopen.side_effect = [res1, res2]

        import src.rabbitmq.manage_queues as manage_queues

        # We need a way to call the test-connection logic
        # without running the whole script
        # I'll implement a function called 'test_connection'
        try:
            manage_queues.test_connection()
        except AttributeError:
            self.fail("test_connection() function not implemented in manage_queues.py")

    @patch("urllib.request.urlopen")
    def test_check_system_status_details(self, mock_urlopen: Any) -> None:
        import io
        import json
        from contextlib import redirect_stdout
        from unittest.mock import MagicMock

        # overview response
        res1 = MagicMock()
        res1.__enter__.return_value = res1
        res1.read.return_value = json.dumps(
            {
                "rabbitmq_version": "3.13.0",
                "cluster_name": "test-cluster",
                "queue_totals": {"messages": 100},
                "object_totals": {"queues": 5, "connections": 2, "channels": 4},
            }
        ).encode()
        res1.status = 200

        # nodes response
        res2 = MagicMock()
        res2.__enter__.return_value = res2
        res2.read.return_value = json.dumps(
            [
                {
                    "name": "rabbit@node1",
                    "running": True,
                    "alarms": [],
                    "mem_used": 100 * 1024 * 1024,
                    "mem_limit": 200 * 1024 * 1024,
                    "fd_used": 50,
                    "fd_total": 1024,
                    "proc_used": 100,
                    "proc_total": 1048576,
                    "disk_free": 1000 * 1024 * 1024,
                    "disk_free_limit": 50 * 1024 * 1024,
                }
            ]
        ).encode()
        res2.status = 200

        mock_urlopen.side_effect = [res1, res2]

        import src.rabbitmq.manage_queues as manage_queues

        f = io.StringIO()
        with redirect_stdout(f):
            manage_queues.check_system_status()
        output = f.getvalue()

        self.assertIn("FD Usage", output)
        self.assertIn("Proc Usage", output)
        self.assertIn("Memory (MB/Limit)", output)

    @patch("urllib.request.urlopen")
    def test_check_system_status_with_alarms(self, mock_urlopen: Any) -> None:
        import io
        import json
        from contextlib import redirect_stdout
        from unittest.mock import MagicMock

        # overview response
        res1 = MagicMock()
        res1.__enter__.return_value = res1
        res1.read.return_value = json.dumps(
            {
                "rabbitmq_version": "3.13.0",
                "cluster_name": "test-cluster",
                "queue_totals": {"messages": 100},
                "object_totals": {"queues": 5, "connections": 2, "channels": 4},
            }
        ).encode()
        res1.status = 200

        # nodes response with memory alarm
        res2 = MagicMock()
        res2.__enter__.return_value = res2
        res2.read.return_value = json.dumps(
            [
                {
                    "name": "rabbit@node1",
                    "running": True,
                    "alarms": ["memory"],
                    "mem_used": 190 * 1024 * 1024,
                    "mem_limit": 200 * 1024 * 1024,
                    "fd_used": 50,
                    "fd_total": 1024,
                    "proc_used": 100,
                    "proc_total": 1048576,
                    "disk_free": 1000 * 1024 * 1024,
                    "disk_free_limit": 50 * 1024 * 1024,
                }
            ]
        ).encode()
        res2.status = 200

        mock_urlopen.side_effect = [res1, res2]

        import src.rabbitmq.manage_queues as manage_queues

        f = io.StringIO()
        with redirect_stdout(f):
            manage_queues.check_system_status()
        output = f.getvalue()

        self.assertIn("ACTIVE ALARMS DETECTED", output)
        self.assertIn("Node rabbit@node1: memory", output)

    @patch("urllib.request.urlopen")
    @patch("subprocess.run")
    @patch.dict("os.environ", {"RMQ_HOST": "10.0.0.5"})
    def test_grow_members_remote_no_cli_fallback(
        self, mock_run: Any, mock_urlopen: Any
    ) -> None:
        import importlib
        import io
        import json
        from contextlib import redirect_stdout
        from unittest.mock import MagicMock

        import src.rabbitmq.manage_queues as manage_queues

        importlib.reload(manage_queues)

        # 1. Mocking /api/nodes (target node exists)
        res1 = MagicMock()
        res1.__enter__.return_value = res1
        res1.read.return_value = json.dumps([{"name": "rabbit@remote1"}]).encode()
        res1.status = 200

        # 2. Mocking /api/overview (version 3.12.0 - API not supported)
        res2 = MagicMock()
        res2.__enter__.return_value = res2
        res2.read.return_value = json.dumps({"rabbitmq_version": "3.12.0"}).encode()
        res2.status = 200

        mock_urlopen.side_effect = [res1, res2]

        f = io.StringIO()
        with redirect_stdout(f):
            manage_queues.grow_members("rabbit@remote1")
        output = f.getvalue()

        # Verify that subprocess.run was NOT called (no docker exec)
        mock_run.assert_not_called()
        self.assertIn("CLI fallback is only supported for local environments", output)
        self.assertIn("Target host '10.0.0.5' is remote", output)


if __name__ == "__main__":
    unittest.main()
