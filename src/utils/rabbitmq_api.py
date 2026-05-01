import base64
import urllib.request
from typing import Any, Optional


class RabbitMQClient:
    """Client for interacting with RabbitMQ Management API."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 15672,
        user: str = "guest",
        password: str = "guest",  # noqa: S107
        use_ssl: bool = False,
    ):
        protocol = "https" if use_ssl else "http"
        self.base_url = f"{protocol}://{host}:{port}/api"
        auth_str = f"{user}:{password}"
        self.auth_header = "Basic " + base64.b64encode(auth_str.encode()).decode()

    def _request(
        self, path: str, method: str = "GET", data: Optional[bytes] = None
    ) -> Any:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method=method, data=data)  # noqa: S310
        req.add_header("Authorization", self.auth_header)
        if data:
            req.add_header("Content-Type", "application/json")

        # S310: URL scheme is controlled by base_url
        with urllib.request.urlopen(req) as response:  # noqa: S310
            if response.status == 204:
                return None
            return response.read()

    def delete_queue(self, vhost: str, name: str) -> None:
        """Delete a single queue."""
        encoded_vhost = vhost.replace("/", "%2f")
        self._request(f"/queues/{encoded_vhost}/{name}", method="DELETE")
