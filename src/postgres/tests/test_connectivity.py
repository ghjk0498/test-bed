import unittest
from unittest.mock import MagicMock, patch

from src.postgres.db_client import PostgresClient


class TestPostgresClient(unittest.TestCase):
    def test_client_init_defaults(self) -> None:
        client = PostgresClient()
        self.assertEqual(client.user, "admin")
        self.assertEqual(client.dbname, "testdb")

    @patch("subprocess.run")
    def test_check_connection_success(self, mock_run: MagicMock) -> None:
        # Mocking successful SELECT 1;
        mock_run.return_value = MagicMock(
            returncode=0, stdout=" 1\n(1 row)\n", stderr=""
        )

        client = PostgresClient()
        self.assertTrue(client.check_connection())

        # Verify the command
        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertIn("psql", cmd)
        self.assertIn("SELECT 1;", cmd)

    @patch("subprocess.run")
    def test_check_connection_failure(self, mock_run: MagicMock) -> None:
        # Mocking failed connection
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error: could not connect"
        )

        client = PostgresClient()
        self.assertFalse(client.check_connection())


if __name__ == "__main__":
    unittest.main()
