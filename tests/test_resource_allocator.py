import pytest
import json
from resource_management_agent.tools.resource_allocator import ResourceAllocator
from utils.error_handling import RetryError

def test_resource_allocation_success(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test successful resource allocation"""
    test_request = {
        "type": "heavy_equipment",
        "quantity": 2,
        "equipment": "excavator",
        "duration": "2 weeks",
        "project": "Site A Foundation",
        "start_date": "2024-03-15"
    }
    
    tool = ResourceAllocator(
        resource_request=test_request,
        priority_level="high"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_resource_availability_check(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test resource availability verification"""
    # Set up mock available resources
    mock_redis_client.set(
        "resource_availability",
        json.dumps({
            "heavy_equipment": {
                "excavator": 3,
                "crane": 2
            }
        })
    )
    
    test_request = {
        "type": "heavy_equipment",
        "quantity": 1,
        "equipment": "excavator",
        "duration": "1 week"
    }
    
    tool = ResourceAllocator(
        resource_request=test_request,
        priority_level="medium"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_resource_conflict_handling(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test handling of resource conflicts"""
    # Set up existing allocation
    mock_duckdb_connection.execute("""
        INSERT INTO resource_allocations 
        (request_details, priority, allocation_plan)
        VALUES (?, ?, ?)
    """, (
        '{"type": "heavy_equipment", "equipment": "excavator"}',
        "high",
        "Existing allocation"
    ))
    
    test_request = {
        "type": "heavy_equipment",
        "quantity": 1,
        "equipment": "excavator",
        "duration": "1 week"
    }
    
    tool = ResourceAllocator(
        resource_request=test_request,
        priority_level="low"
    )
    
    result = tool.run()
    assert "conflict" in result.lower()

def test_resource_allocation_validation():
    """Test validation of resource requests"""
    # Test missing required fields
    with pytest.raises(ValueError):
        ResourceAllocator(
            resource_request={},  # Empty request
            priority_level="high"
        )
    
    # Test invalid priority level
    with pytest.raises(ValueError):
        ResourceAllocator(
            resource_request={"type": "equipment", "quantity": 1},
            priority_level="invalid_priority"
        )

def test_resource_notification(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test resource allocation notifications"""
    test_request = {
        "type": "labor",
        "quantity": 5,
        "role": "carpenter",
        "duration": "1 month"
    }
    
    tool = ResourceAllocator(
        resource_request=test_request,
        priority_level="high"
    )
    
    result = tool.run()
    
    # Verify Redis notification was sent
    published_messages = mock_redis_client.published_messages
    assert len(published_messages) > 0
    assert "resource_updates" in published_messages[0]["channel"]

def test_allocation_persistence(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test persistence of allocation data"""
    test_request = {
        "type": "materials",
        "quantity": 1000,
        "material": "concrete",
        "unit": "cubic_yards"
    }
    
    tool = ResourceAllocator(
        resource_request=test_request,
        priority_level="medium"
    )
    
    result = tool.run()
    
    # Verify allocation was stored
    stored_allocations = mock_duckdb_connection.execute(
        "SELECT * FROM resource_allocations"
    ).fetchall()
    assert len(stored_allocations) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 