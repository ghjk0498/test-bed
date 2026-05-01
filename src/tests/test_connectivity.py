import unittest
from unittest.mock import patch
from src.utils.rabbitmq_api import RabbitMQClient

class TestRabbitMQClientConnectivity(unittest.TestCase):
    def test_client_defaults_to_http(self):
        client = RabbitMQClient(host="localhost", port=15672)
        self.assertEqual(client.base_url, "http://localhost:15672/api")

    def test_client_supports_https(self):
        client = RabbitMQClient(host="remote-host", port=15671, use_ssl=True)
        self.assertEqual(client.base_url, "https://remote-host:15671/api")

    @patch("urllib.request.urlopen")
    def test_test_connection_logic(self, mock_urlopen):
        # Mocking /api/whoami and /api/overview
        import json
        from unittest.mock import MagicMock
        
        # whoami response
        res1 = MagicMock()
        res1.__enter__.return_value = res1
        res1.read.return_value = json.dumps({"name": "guest", "tags": ["administrator"]}).encode()
        res1.status = 200
        
        # overview response
        res2 = MagicMock()
        res2.__enter__.return_value = res2
        res2.read.return_value = json.dumps({"rabbitmq_version": "3.13.0"}).encode()
        res2.status = 200
        
        mock_urlopen.side_effect = [res1, res2]
        
        import src.scripts.manage_queues as manage_queues
        # We need a way to call the test-connection logic without running the whole script
        # I'll implement a function called 'test_connection'
        try:
            manage_queues.test_connection()
        except AttributeError:
            self.fail("test_connection() function not implemented in manage_queues.py")

if __name__ == "__main__":
    unittest.main()
