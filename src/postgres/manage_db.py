import argparse
import sys

from src.postgres.db_client import PostgresClient


def status() -> None:
    """Check and display the status of the PostgreSQL database."""
    client = PostgresClient()
    if client.check_connection():
        print("[OK] PostgreSQL is reachable and responding.")
        # Try to get some info
        res = client.execute_query("SELECT version();")
        if res.returncode == 0:
            print(f"Version: {res.stdout.strip()}")
    else:
        print("[ERROR] Could not connect to PostgreSQL.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="PostgreSQL Management Script")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    subparsers.add_parser("status", help="Check database status")

    args = parser.parse_args()

    if args.command == "status":
        status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
