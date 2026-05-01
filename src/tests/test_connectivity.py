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

    @patch.dict("os.environ", {"RMQ_USE_SSL": "true", "RMQ_HOST": "secure-rmq"})
    def test_manage_queues_url_construction(self):
        # manage_queues.py를 다시 로드하여 환경 변수가 반영되도록 함
        import importlib
        import src.scripts.manage_queues as manage_queues
        importlib.reload(manage_queues)
        
        self.assertTrue(manage_queues.RABBIT_URL.startswith("https://"))
        self.assertIn("secure-rmq", manage_queues.RABBIT_URL)

if __name__ == "__main__":
    unittest.main()
