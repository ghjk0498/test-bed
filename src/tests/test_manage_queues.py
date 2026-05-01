import pytest
from src.scripts.manage_queues import generate_definitions, is_balanced, is_api_supported

def test_generate_definitions():
    """Test if generate_definitions creates the correct number of queue definitions."""
    n = 10
    defs = generate_definitions(n)
    
    assert "queues" in defs
    assert len(defs["queues"]) == n
    assert defs["queues"][0]["name"] == "Q00000001"
    assert defs["queues"][-1]["name"] == "Q00000010"
    assert defs["queues"][0]["arguments"]["x-queue-type"] == "quorum"

def test_is_balanced():
    """Test the balance detection logic."""
    # Balanced
    assert is_balanced({"node1": 10, "node2": 10, "node3": 10}) is True
    assert is_balanced({"node1": 10, "node2": 11, "node3": 10}) is True
    
    # Unbalanced
    assert is_balanced({"node1": 10, "node2": 12, "node3": 10}) is False
    assert is_balanced({"node1": 0, "node2": 2, "node3": 1}) is False
    
    # Empty
    assert is_balanced({}) is True

def test_is_api_supported_logic():
    """Test the version comparison logic for API support (>= 3.13)."""
    assert is_api_supported("3.13.0") is True
    assert is_api_supported("3.13.1") is True
    assert is_api_supported("4.0.0") is True
    assert is_api_supported("3.12.9") is False
    assert is_api_supported("3.9.13") is False
    assert is_api_supported("2.8.0") is False
    assert is_api_supported("") is False
    assert is_api_supported("unknown") is False
