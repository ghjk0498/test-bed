import argparse
import base64
import json
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# RabbitMQ 연결 정보 (환경에 맞게 수정)
RABBIT_URL = "http://localhost:15672"
AUTH_HEADER = "Basic " + base64.b64encode(b"guest:guest").decode("utf-8")
HEADERS = {"Authorization": AUTH_HEADER, "Content-Type": "application/json"}


def get_rabbitmq_version() -> str:
    """Fetch the RabbitMQ version from the /api/overview endpoint."""
    url = f"{RABBIT_URL}/api/overview"
    if not url.startswith("http"):
        return ""

    req = urllib.request.Request(url, headers=HEADERS)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as res:  # noqa: S310
            data = json.loads(res.read().decode("utf-8"))
            return str(data.get("rabbitmq_version", ""))
    except Exception as e:
        print(f"Error fetching version: {e}")
        return ""


def is_api_supported(version: str) -> bool:
    """Check if the RabbitMQ version supports Quorum Queue replica API (>= 3.13)."""
    if not version:
        return False
    try:
        # Simple version comparison for 3.13.x
        parts = [int(p) for p in version.split(".") if p.isdigit()]
        if not parts:
            return False
        if parts[0] > 3:
            return True
        if parts[0] == 3 and len(parts) >= 2 and parts[1] >= 13:
            return True
        return False
    except (ValueError, IndexError):
        return False


def generate_definitions(n: int) -> dict[str, Any]:
    """Generate RabbitMQ definitions for bulk import."""
    queues = [
        {
            "name": f"Q{i:08d}",
            "vhost": "/",
            "durable": True,
            "auto_delete": False,
            "arguments": {"x-queue-type": "quorum"},
        }
        for i in range(1, n + 1)
    ]
    return {
        "queues": queues,
        "exchanges": [],
        "bindings": [],
        "users": [],
        "vhosts": [],
    }


def create_queues(n: int) -> None:
    """Create queues using a single HTTP API call (Fastest for bulk creation)."""
    definitions = generate_definitions(n)

    print(f"Importing {n} queues via HTTP API...")
    url = f"{RABBIT_URL}/api/definitions"
    # S310: Validate scheme
    if not url.startswith("http"):
        raise ValueError(f"Invalid URL: {url}")

    req = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(definitions).encode("utf-8"),
        headers=HEADERS,
        method="POST",
    )

    # 단 한 번의 HTTP 요청으로 n개의 큐를 즉시 생성
    with urllib.request.urlopen(req) as res:  # noqa: S310
        if res.status in (200, 201, 204):
            print("Successfully created queues.")
        else:
            print(f"Failed: {res.status}")


def delete_single_queue(i: int) -> None:
    """Worker function to delete a single queue."""
    q_name = f"Q{i:08d}"
    url = f"{RABBIT_URL}/api/queues/%2f/{q_name}"
    if not url.startswith("http"):
        return

    req = urllib.request.Request(url, headers=HEADERS, method="DELETE")  # noqa: S310
    try:
        with urllib.request.urlopen(req):  # noqa: S310
            pass
    except Exception:  # noqa: S110
        pass  # 큐가 없거나 삭제 실패해도 무시


def delete_queues(n: int) -> None:
    """Delete queues concurrently using ThreadPool (Fastest for specific queues)."""
    print(f"Deleting {n} queues using concurrent HTTP requests...")

    # 50개의 스레드를 띄워 병렬로 삭제 요청을 보냄 (속도 대폭 향상)
    with ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(delete_single_queue, range(1, n + 1))

    print("Successfully deleted queues.")


def get_cluster_nodes() -> list[str]:
    """Fetch all node names in the cluster."""
    url = f"{RABBIT_URL}/api/nodes"
    if not url.startswith("http"):
        return []

    req = urllib.request.Request(url, headers=HEADERS)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as res:  # noqa: S310
            nodes = json.loads(res.read().decode("utf-8"))
            return [node.get("name") for node in nodes if node.get("name")]
    except Exception as e:
        print(f"Error fetching nodes: {e}")
        return []


def get_leader_distribution() -> dict[str, int]:
    """Fetch current leader distribution for all nodes (including 0-count nodes)."""
    # 1. Get all nodes first to ensure we account for nodes with 0 leaders
    all_nodes = get_cluster_nodes()
    dist = {node: 0 for node in all_nodes}

    # 2. Fetch queues and count leaders
    url = f"{RABBIT_URL}/api/queues"
    if not url.startswith("http"):
        return dist

    req = urllib.request.Request(url, headers=HEADERS)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as res:  # noqa: S310
            queues = json.loads(res.read().decode("utf-8"))
            if not queues:
                return dist

            # Filter out None and handle them as "No Leader"
            for q in queues:
                node = q.get("node")
                if node is None:
                    node = "Unknown/No Leader"

                if node in dist:
                    dist[node] += 1
                else:
                    dist[node] = 1
            return dist
    except Exception as e:
        print(f"Error fetching distribution: {e}")
        return dist


def print_distribution(counts: dict[str, int]) -> None:
    """Print the distribution dictionary in a formatted table."""
    total = sum(counts.values())
    print(f"\nTotal Queues: {total}")
    print("-" * 45)
    print(f"{'Node Name':<30} | {'Leader Count'}")
    print("-" * 45)

    if not counts:
        print("No node data available.")
    else:
        # Ensure node is never None during sorting or printing
        for node, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            display_node = str(node) if node is not None else "Unknown/No Leader"
            print(f"{display_node:<30} | {count} queues")
    print("-" * 45)


def is_balanced(counts: dict[str, int]) -> bool:
    """Check if the distribution is balanced (diff between max and min <= 1)."""
    if not counts:
        return True
    vals = list(counts.values())
    return max(vals) - min(vals) <= 1


def rebalance_queues() -> None:
    """Send a rebalance request for quorum queue leaders (Async)."""
    dist = get_leader_distribution()
    if is_balanced(dist):
        print("Cluster is already balanced. No action needed.")
        return

    print("Sending rebalance request...")
    url = f"{RABBIT_URL}/api/rebalance/queues"
    req = urllib.request.Request(url, headers=HEADERS, method="POST")  # noqa: S310
    try:
        with urllib.request.urlopen(req) as res:  # noqa: S310
            if res.status not in (200, 201, 204):
                print(f"Failed to submit rebalancing request: {res.status}")
                return
            print("Rebalancing request submitted successfully (Async).")
            print("Use 'make dist' to check the distribution status later.")
    except Exception as e:
        print(f"Error during rebalancing: {e}")


def grow_members(node: str) -> None:
    """Add a node as a member to all quorum queues (Hybrid: API or CLI)."""
    version = get_rabbitmq_version()
    if is_api_supported(version):
        print(f"Using HTTP API for 'grow' (RabbitMQ {version})")
        url = f"{RABBIT_URL}/api/queues/quorum/replicas/on/{node}/grow"
        req = urllib.request.Request(url, headers=HEADERS, method="POST")  # noqa: S310
        try:
            with urllib.request.urlopen(req) as res:  # noqa: S310
                if res.status in (200, 201, 204):
                    print(f"Successfully triggered grow on node {node} via API.")
                else:
                    print(f"Failed to grow via API: {res.status}")
        except Exception as e:
            print(f"Error during API grow: {e}")
    else:
        print(f"Falling back to CLI for 'grow' (RabbitMQ {version or 'unknown'})")
        try:
            # Note: Using rabbit1 as the entry point for docker exec
            cmd = ["docker", "exec", "rabbit1", "rabbitmq-queues", "grow", node, "all"]
            subprocess.run(cmd, check=True)  # noqa: S603
            print(f"Successfully executed grow on node {node} via CLI.")
        except Exception as e:
            print(f"Error during CLI grow: {e}")


def shrink_members(node: str) -> None:
    """Remove a node from all quorum queues (Hybrid: API or CLI)."""
    version = get_rabbitmq_version()
    if is_api_supported(version):
        print(f"Using HTTP API for 'shrink' (RabbitMQ {version})")
        url = f"{RABBIT_URL}/api/queues/quorum/replicas/on/{node}/shrink"
        req = urllib.request.Request(
            url, headers=HEADERS, method="DELETE"
        )  # noqa: S310
        try:
            with urllib.request.urlopen(req) as res:  # noqa: S310
                if res.status in (200, 201, 204):
                    print(f"Successfully triggered shrink on node {node} via API.")
                else:
                    print(f"Failed to shrink via API: {res.status}")
        except Exception as e:
            print(f"Error during API shrink: {e}")
    else:
        print(f"Falling back to CLI for 'shrink' (RabbitMQ {version or 'unknown'})")
        try:
            cmd = ["docker", "exec", "rabbit1", "rabbitmq-queues", "shrink", node]
            subprocess.run(cmd, check=True)  # noqa: S603
            print(f"Successfully executed shrink on node {node} via CLI.")
        except Exception as e:
            print(f"Error during CLI shrink: {e}")


def check_queue_distribution() -> None:
    """Check and print how many queues each node is leading."""
    print("Checking queue leader distribution across the cluster...")
    dist = get_leader_distribution()
    print_distribution(dist)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RabbitMQ Fast Management Script")
    parser.add_argument(
        "action",
        choices=["create", "delete", "rebalance", "dist", "grow", "shrink"],
        help="Action to perform",
    )
    parser.add_argument(
        "--n", type=int, default=5, help="Number of queues or target count"
    )
    parser.add_argument(
        "--node", type=str, default="rabbit@rabbit2", help="Target node for grow/shrink"
    )
    args = parser.parse_args()

    if args.action == "create":
        create_queues(args.n)
    elif args.action == "delete":
        delete_queues(args.n)
    elif args.action == "rebalance":
        rebalance_queues()
    elif args.action == "dist":
        check_queue_distribution()
    elif args.action == "grow":
        grow_members(args.node)
    elif args.action == "shrink":
        shrink_members(args.node)
