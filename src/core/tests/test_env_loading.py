import os
import tempfile
import unittest


class TestEnvLoading(unittest.TestCase):
    def test_env_file_loading_logic(self) -> None:
        """Test the logic that reads a .env file and updates os.environ."""
        # This function 'load_env_file' does not exist yet.
        # It should read a file with KEY=VALUE pairs and set them in os.environ.

        env_content = "RMQ_HOST=production-host\nRMQ_PORT=15671\nRMQ_USE_SSL=true"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write(env_content)
            tmp_path = tmp.name

        try:
            # RED: This will fail because load_env_file is not implemented
            import src.rabbitmq.manage_queues as manage_queues

            if hasattr(manage_queues, "load_env_file"):
                manage_queues.load_env_file(tmp_path)
                self.assertEqual(os.environ.get("RMQ_HOST"), "production-host")
                self.assertEqual(os.environ.get("RMQ_PORT"), "15671")
                self.assertEqual(os.environ.get("RMQ_USE_SSL"), "true")
            else:
                self.fail(
                    "load_env_file() function not implemented in manage_queues.py"
                )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            # Cleanup env vars set during test
            for key in ["RMQ_HOST", "RMQ_PORT", "RMQ_USE_SSL"]:
                if key in os.environ:
                    del os.environ[key]


if __name__ == "__main__":
    unittest.main()
