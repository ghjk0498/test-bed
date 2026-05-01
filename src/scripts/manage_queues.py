import argparse
import base64
import json
import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# ruff: noqa: E501, S310

# RabbitMQ 연결 정보 (환경 변수 또는 기본값 사용)
RMQ_HOST = os.getenv("RMQ_HOST", "localhost")
RMQ_PORT = os.getenv("RMQ_PORT", "15672")
RMQ_USER = os.getenv("RMQ_USER", "guest")
RMQ_PASS = os.getenv("RMQ_PASSWORD", "guest")
RMQ_USE_SSL = os.getenv("RMQ_USE_SSL", "false").lower() == "true"

PROTOCOL = "https" if RMQ_USE_SSL else "http"
RABBIT_URL = f"{PROTOCOL}://{RMQ_HOST}:{RMQ_PORT}"
AUTH_STR = f"{RMQ_USER}:{RMQ_PASS}"
AUTH_HEADER = "Basic " + base64.b64encode(AUTH_STR.encode("utf-8")).decode("utf-8")
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


def is_local() -> bool:
    """Check if we are targeting a local RabbitMQ instance."""
    return RMQ_HOST in ("localhost", "127.0.0.1")


def grow_members(node: str) -> None:
    """Add a node as a member to all quorum queues (Hybrid: API or CLI)."""
    # 1. Validate node existence first
    all_nodes = get_cluster_nodes()
    if node not in all_nodes:
        print(f"Error: Node '{node}' is not a member of the cluster.")
        print(f"Available nodes: {', '.join(all_nodes)}")
        return

    version = get_rabbitmq_version()
    if is_api_supported(version):
        print(f"Using HTTP API for 'grow' (RabbitMQ {version})")
        url = f"{RABBIT_URL}/api/queues/quorum/replicas/on/{node}/grow"
        req = urllib.request.Request(url, headers=HEADERS, method="POST")  # noqa: S310
        try:
            with urllib.request.urlopen(req) as res:  # noqa: S310
                if res.status in (200, 201, 204):
                    print(f"Successfully triggered grow on node {node} via API.")
                    print(
                        "Note: New members added. Run 'rebalance' to distribute leaders."
                    )  # noqa: E501
                else:
                    print(f"Failed to grow via API: {res.status}")
        except Exception as e:
            print(f"Error during API grow: {e}")
    elif is_local():
        print(f"Falling back to CLI for 'grow' (RabbitMQ {version or 'unknown'})")
        try:
            # Note: Using rabbit1 as the entry point for docker exec
            cmd = ["docker", "exec", "rabbit1", "rabbitmq-queues", "grow", node, "all"]
            result = subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, check=False
            )

            # Check for various failure patterns in output
            output = (result.stdout + result.stderr).lower()
            if result.returncode == 0 and not any(
                x in output for x in ["error", "failed", "unable", "invalid"]
            ):
                print(f"Successfully executed grow on node {node} via CLI.")
                print("Note: New members added. Run 'rebalance' to distribute leaders.")
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                print(f"Failed to grow on node {node} via CLI:\n{error_msg}")
        except Exception as e:
            print(f"Error executing CLI grow: {e}")
    else:
        print("Error: CLI fallback is only supported for local environments.")
        print(
            f"Target host '{RMQ_HOST}' is remote and RabbitMQ version '{version}' "
            "does not support Grow API."
        )
        print("Please upgrade RabbitMQ to >= 3.13 for remote Grow/Shrink support.")


def shrink_members(node: str) -> None:
    """Remove a node from all quorum queues (Hybrid: API or CLI)."""
    # 1. Validate node existence first
    all_nodes = get_cluster_nodes()
    if node not in all_nodes:
        print(f"Error: Node '{node}' is not a member of the cluster.")
        print(f"Available nodes: {', '.join(all_nodes)}")
        return

    version = get_rabbitmq_version()
    if is_api_supported(version):
        print(f"Using HTTP API for 'shrink' (RabbitMQ {version})")
        url = f"{RABBIT_URL}/api/queues/quorum/replicas/on/{node}/shrink"
        req = urllib.request.Request(  # noqa: S310
            url, headers=HEADERS, method="DELETE"
        )
        try:
            with urllib.request.urlopen(req) as res:  # noqa: S310
                if res.status in (200, 201, 204):
                    print(f"Successfully triggered shrink on node {node} via API.")
                else:
                    print(f"Failed to shrink via API: {res.status}")
        except Exception as e:
            print(f"Error during API shrink: {e}")
    elif is_local():
        print(f"Falling back to CLI for 'shrink' (RabbitMQ {version or 'unknown'})")
        try:
            cmd = ["docker", "exec", "rabbit1", "rabbitmq-queues", "shrink", node]
            result = subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, check=False
            )

            output = (result.stdout + result.stderr).lower()
            if result.returncode == 0 and not any(
                x in output for x in ["error", "failed", "unable", "invalid"]
            ):
                print(f"Successfully executed shrink on node {node} via CLI.")
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                print(f"Failed to shrink on node {node} via CLI:\n{error_msg}")
        except Exception as e:
            print(f"Error executing CLI shrink: {e}")
    else:
        print(
            "Error: CLI fallback is only supported for local environments (localhost)."
        )
        print(
            f"Target host '{RMQ_HOST}' is remote and RabbitMQ version '{version}' "
            "does not support Shrink API."
        )  # noqa: E501
        print("Please upgrade RabbitMQ to >= 3.13 for remote Grow/Shrink support.")


def check_queue_distribution() -> None:
    """Check and print how many queues each node is leading."""
    print("Checking queue leader distribution across the cluster...")
    dist = get_leader_distribution()
    print_distribution(dist)


def check_queue_details(limit: int = 10) -> None:
    """Fetch and print detailed status of individual queues."""
    print(f"Fetching details for top {limit} queues...\n")
    url = f"{RABBIT_URL}/api/queues"
    if not url.startswith("http"):
        return

    req = urllib.request.Request(url, headers=HEADERS)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as res:  # noqa: S310
            queues = json.loads(res.read().decode("utf-8"))
            if not queues:
                print("No queues found.")
                return

            print(
                f"{'Queue Name':<15} | {'Msg':>5} | {'Ready':>5} | {'Unack':>5} | "
                f"{'Status':<8} | {'Leader':<15} | {'Sync Replicas'}"
            )
            print("-" * 90)

            # Sort by message count descending
            queues.sort(key=lambda x: x.get("messages", 0), reverse=True)

            for q in queues[:limit]:
                name = q.get("name", "Unknown")
                msgs = q.get("messages", 0)
                ready = q.get("messages_ready", 0)
                unack = q.get("messages_unacknowledged", 0)
                state = q.get("state", "unknown")
                leader = q.get("node", "None")

                # Quorum queue specific: synchronized replicas
                sync = q.get("synchronised_slave_nodes", [])
                sync_str = ", ".join(sync) if sync else "N/A"

                print(
                    f"{name:<15} | {msgs:>5} | {ready:>5} | {unack:>5} | "
                    f"{state:<8} | {leader:<15} | {sync_str}"
                )

            if len(queues) > limit:
                print(f"\n... and {len(queues) - limit} more queues.")
    except Exception as e:
        print(f"Error fetching queue details: {e}")


def check_queue_summary() -> None:
    """Print a high-level summary of all queues (types, states, total messages)."""
    print("Fetching queue summary...\n")
    url = f"{RABBIT_URL}/api/queues"
    if not url.startswith("http"):
        return

    req = urllib.request.Request(url, headers=HEADERS)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as res:  # noqa: S310
            queues = json.loads(res.read().decode("utf-8"))
            if not queues:
                print("No queues found.")
                return

            total_queues = len(queues)
            types: dict[str, int] = {}
            states: dict[str, int] = {}
            replica_counts: dict[int, int] = {}
            at_risk_queues = 0
            total_msgs = 0
            total_ready = 0
            total_unack = 0

            for q in queues:
                # Type (quorum, classic, etc.)
                q_type = q.get("type", "classic")
                types[q_type] = types.get(q_type, 0) + 1

                # State (running, idle, etc.)
                q_state = q.get("state", "unknown")
                states[q_state] = states.get(q_state, 0) + 1

                # Replica Count (Quorum specific)
                # For quorum queues, members are in 'members' + leader
                members = q.get("members", [])
                r_count = len(members)
                if r_count > 0:
                    replica_counts[r_count] = replica_counts.get(r_count, 0) + 1
                    # Risk assessment: Quorum queues should have >= 3 nodes and odd count
                    if r_count < 3 or r_count % 2 == 0:
                        at_risk_queues += 1

                # Messages
                total_msgs += q.get("messages", 0)
                total_ready += q.get("messages_ready", 0)
                total_unack += q.get("messages_unacknowledged", 0)

            print(f"Total Queues: {total_queues}")
            print("-" * 30)
            print("By Type:")
            for t, count in types.items():
                print(f"  - {t:<10}: {count}")

            print("\nBy State:")
            for s, count in states.items():
                print(f"  - {s:<10}: {count}")

            print("\nReplica Distribution (Quorum):")
            if not replica_counts:
                print("  - No quorum data available.")
            else:
                for rc, count in sorted(replica_counts.items()):
                    risk_note = " (Low Redundancy!)" if rc < 3 else ""
                    if rc % 2 == 0:
                        risk_note += " (Even Number - Not Optimal)"
                    print(f"  - {rc} replicas: {count} queues{risk_note}")

                if at_risk_queues > 0:
                    print(
                        f"\n  [!] WARNING: {at_risk_queues} queues have sub-optimal replica counts."
                    )

            print("\nMessage Totals:")
            print(f"  - Total      : {total_msgs}")
            print(f"  - Ready      : {total_ready}")
            print(f"  - Unack      : {total_unack}")

            if total_queues > 0:
                print("\nAverages:")
                print(f"  - Msgs/Queue : {total_msgs / total_queues:.2f}")

    except Exception as e:
        print(f"Error fetching queue summary: {e}")


def check_system_status() -> None:
    """Check and print the overall health and status of the RabbitMQ cluster."""
    print("Fetching RabbitMQ system status...\n")

    url = f"{RABBIT_URL}/api/overview"
    if not url.startswith("http"):
        return

    req = urllib.request.Request(url, headers=HEADERS)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as res:  # noqa: S310
            overview = json.loads(res.read().decode("utf-8"))
            version = overview.get("rabbitmq_version", "Unknown")
            cluster_name = overview.get("cluster_name", "Unknown")

            queue_totals = overview.get("queue_totals", {})
            total_messages = queue_totals.get("messages", 0)

            object_totals = overview.get("object_totals", {})
            total_queues = object_totals.get("queues", 0)
            total_connections = object_totals.get("connections", 0)
            total_channels = object_totals.get("channels", 0)

            print(f"Cluster Name:      {cluster_name}")
            print(f"RabbitMQ Version:  {version}")
            print(f"Total Queues:      {total_queues}")
            print(f"Total Connections: {total_connections}")
            print(f"Total Channels:    {total_channels}")
            print(f"Total Messages:    {total_messages}\n")

    except Exception as e:
        print(f"Error fetching cluster overview: {e}")
        return

    # Fetch individual node statuses
    nodes_url = f"{RABBIT_URL}/api/nodes"
    req_nodes = urllib.request.Request(nodes_url, headers=HEADERS)  # noqa: S310
    try:
        with urllib.request.urlopen(req_nodes) as res:  # noqa: S310
            nodes = json.loads(res.read().decode("utf-8"))
            print(
                f"{'Node Name':<20} | {'Status':<10} | {'Alarms':<15} | "
                f"{'Memory (MB)':<15} | {'Disk Free (MB)':<15}"
            )
            print("-" * 85)
            for node in nodes:
                name = node.get("name", "Unknown")
                running = node.get("running", False)
                status = "Running" if running else "Down"

                # Check alarms
                alarms = node.get("alarms", [])
                alarms_str = ", ".join(alarms) if alarms else "OK"

                # Memory (convert bytes to MB)
                mem_used = node.get("mem_used", 0) / (1024 * 1024)

                # Disk Free (convert bytes to MB)
                disk_free = node.get("disk_free", 0) / (1024 * 1024)

                print(
                    f"{name:<20} | {status:<10} | {alarms_str:<15} | "
                    f"{mem_used:<15.2f} | {disk_free:<15.2f}"
                )
    except Exception as e:
        print(f"Error fetching nodes status: {e}")


def export_definitions(file_path: str) -> None:
    """Export RabbitMQ definitions to a JSON file."""
    print(f"Exporting definitions to {file_path}...")
    url = f"{RABBIT_URL}/api/definitions"
    if not url.startswith("http"):
        return

    req = urllib.request.Request(url, headers=HEADERS)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as res:  # noqa: S310
            definitions = json.loads(res.read().decode("utf-8"))
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(definitions, f, indent=4)
            print("Definitions exported successfully.")
    except Exception as e:
        print(f"Error exporting definitions: {e}")


def import_definitions(file_path: str) -> None:
    """Import RabbitMQ definitions from a JSON file."""
    print(f"Importing definitions from {file_path}...")
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    url = f"{RABBIT_URL}/api/definitions"
    if not url.startswith("http"):
        return

    try:
        with open(file_path, encoding="utf-8") as f:
            definitions = json.load(f)

        req = urllib.request.Request(
            url,
            data=json.dumps(definitions).encode("utf-8"),
            headers=HEADERS,
            method="POST",
        )  # noqa: S310
        with urllib.request.urlopen(req) as res:  # noqa: S310
            if res.status in (200, 201, 204):
                print("Definitions imported successfully.")
            else:
                print(f"Failed to import: {res.status}")
    except Exception as e:
        print(f"Error importing definitions: {e}")


def test_connection() -> None:
    """Perform a comprehensive connectivity and permission test."""
    print(f"Testing connectivity to: {RABBIT_URL}")
    print("-" * 50)

    # 1. Authentication and Identity
    whoami_url = f"{RABBIT_URL}/api/whoami"
    success = True
    try:
        req = urllib.request.Request(whoami_url, headers=HEADERS)  # noqa: S310
        with urllib.request.urlopen(req) as res:  # noqa: S310
            user_data = json.loads(res.read().decode("utf-8"))
            user_name = user_data.get("name", "Unknown")
            tags = user_data.get("tags", [])
            print(f"[OK] Authentication: Connected as '{user_name}'")
            print(f"     Tags: {', '.join(tags)}")
            if "administrator" not in tags:
                print("     [!] Warning: User is not an administrator. Some actions may fail.")
    except Exception as e:
        print(f"[FAIL] Authentication: {e}")
        success = False

    # 2. Version and API Compatibility
    version = get_rabbitmq_version()
    if version:
        print(f"[OK] RabbitMQ Version: {version}")
        if is_api_supported(version):
            print("     [OK] API: Quorum Replica Management (3.13+) is supported.")
        else:
            print("     [!] API: Quorum Replica Management requires RabbitMQ 3.13+.")
    else:
        print("[FAIL] RabbitMQ Version: Could not retrieve version info.")
        success = False

    # 3. Environment Summary
    env_type = "Local (Docker-aware)" if is_local() else "Remote"
    print(f"[INFO] Environment: {env_type}")
    print(f"[INFO] TLS/SSL: {'Enabled' if RMQ_USE_SSL else 'Disabled'}")

    print("-" * 50)
    if success:
        print("Connection test COMPLETED successfully.")
    else:
        print("Connection test FAILED.")


if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser(description="RabbitMQ Fast Management Script")
    parser.add_argument(
        "action",
        choices=[
            "create",
            "delete",
            "rebalance",
            "dist",
            "grow",
            "shrink",
            "status",
            "queue-status",
            "queue-summary",
            "export-defs",
            "import-defs",
            "test-connection",
        ],
        help="Action to perform",
    )
    parser.add_argument(
        "--n", type=int, default=5, help="Number of queues or target count"
    )
    parser.add_argument(
        "--node", type=str, default="rabbit@rabbit2", help="Target node for grow/shrink"
    )
    parser.add_argument(
        "--file",
        type=str,
        default="definitions.json",
        help="File path for export/import",
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
    elif args.action == "status":
        check_system_status()
    elif args.action == "queue-status":
        check_queue_details(args.n)
    elif args.action == "queue-summary":
        check_queue_summary()
    elif args.action == "export-defs":
        export_definitions(args.file)
    elif args.action == "import-defs":
        import_definitions(args.file)
    elif args.action == "test-connection":
        test_connection()
