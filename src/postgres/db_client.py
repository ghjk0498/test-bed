import os
import subprocess


class PostgresClient:
    """A simple PostgreSQL client using subprocess to psql command."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "admin",
        password: str = "secret_pass",  # noqa: S107
        dbname: str = "testdb",
    ) -> None:
        self.host = os.environ.get("PGHOST", host)
        self.port = int(os.environ.get("PGPORT", str(port)))
        self.user = os.environ.get("PGUSER", user)
        self.password = os.environ.get("PGPASSWORD", password)
        self.dbname = os.environ.get("PGDATABASE", dbname)

    def execute_query(self, query: str) -> subprocess.CompletedProcess[str]:
        """Execute a SQL query using psql via docker exec."""
        # Note: Using docker exec to avoid local dependencies
        cmd = [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={self.password}",
            "postgres",
            "psql",
            "-h",
            "localhost",
            "-U",
            self.user,
            "-d",
            self.dbname,
            "-c",
            query,
        ]
        return subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, check=False
        )

    def check_connection(self) -> bool:
        """Check if the database is reachable."""
        result = self.execute_query("SELECT 1;")
        return result.returncode == 0
