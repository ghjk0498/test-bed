from src.rabbitmq.manage_queues import (
    generate_definitions,
    is_api_supported,
    is_balanced,
)


def test_generate_definitions() -> None:
    """Test the structure and content of generated definitions."""
    n = 10
    defs = generate_definitions(n)

    assert "queues" in defs  # noqa: S101
    assert len(defs["queues"]) == n  # noqa: S101
    assert defs["queues"][0]["name"] == "Q00000001"  # noqa: S101
    assert defs["queues"][-1]["name"] == "Q00000010"  # noqa: S101
    assert defs["queues"][0]["arguments"]["x-queue-type"] == "quorum"  # noqa: S101


def test_is_balanced() -> None:
    """Test the balance detection logic."""
    # Balanced
    assert is_balanced({"node1": 10, "node2": 10, "node3": 10}) is True  # noqa: S101
    assert is_balanced({"node1": 10, "node2": 11, "node3": 10}) is True  # noqa: S101

    # Unbalanced
    assert is_balanced({"node1": 10, "node2": 12, "node3": 10}) is False  # noqa: S101
    assert is_balanced({"node1": 0, "node2": 2, "node3": 1}) is False  # noqa: S101

    # Empty
    assert is_balanced({}) is True  # noqa: S101


def test_is_api_supported_logic() -> None:
    """Test the version comparison logic for API support (>= 3.13)."""
    assert is_api_supported("3.13.0") is True  # noqa: S101
    assert is_api_supported("3.13.1") is True  # noqa: S101
    assert is_api_supported("4.0.0") is True  # noqa: S101
    assert is_api_supported("3.12.9") is False  # noqa: S101
    assert is_api_supported("3.9.13") is False  # noqa: S101
    assert is_api_supported("2.8.0") is False  # noqa: S101
    assert is_api_supported("") is False  # noqa: S101
    assert is_api_supported("unknown") is False  # noqa: S101
