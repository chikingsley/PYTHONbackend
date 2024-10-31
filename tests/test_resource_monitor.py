import pytest
from datetime import datetime
from resource_management_agent.tools.resource_monitor import ResourceMonitor
from utils.error_handling import RetryError

def test_resource_monitoring_success(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test successful resource monitoring"""
    tool = ResourceMonitor(
        project_id="PROJ001",
        monitoring_type="utilization"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_utilization_analysis(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test resource utilization analysis"""
    # Set up mock resource status
    mock_redis_client.set(
        "project_resources:PROJ002",
        json.dumps({
            "equipment": {
                "excavator": {"utilization": 0.75},
                "crane": {"utilization": 0.45}
            }
        })
    )
    
    tool = ResourceMonitor(
        project_id="PROJ002",
        monitoring_type="efficiency"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert "utilization" in result.lower()

def test_alert_generation(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test alert generation for resource issues"""
    # Set up mock data indicating a problem
    mock_redis_client.set(
        "project_resources:PROJ003",
        json.dumps({
            "equipment": {
                "excavator": {"status": "maintenance_required"}
            }
        })
    )
    
    tool = ResourceMonitor(
        project_id="PROJ003",
        monitoring_type="conflicts"
    )
    
    result = tool.run()
    
    # Verify alert was published
    published_messages = mock_redis_client.published_messages
    assert len(published_messages) > 0
    assert "resource_alerts" in published_messages[0]["channel"]

def test_historical_data_analysis(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test analysis of historical utilization data"""
    # Set up mock historical data
    mock_duckdb_connection.execute("""
        INSERT INTO resource_utilization 
        (project_id, resource_type, utilization_rate, timestamp)
        VALUES (?, ?, ?, ?)
    """, ("PROJ004", "crane", 0.85, datetime.now()))
    
    tool = ResourceMonitor(
        project_id="PROJ004",
        monitoring_type="utilization"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_monitoring_validation():
    """Test validation of monitoring parameters"""
    # Test invalid project ID
    with pytest.raises(ValueError):
        ResourceMonitor(
            project_id="",  # Empty project ID
            monitoring_type="utilization"
        )
    
    # Test invalid monitoring type
    with pytest.raises(ValueError):
        ResourceMonitor(
            project_id="PROJ005",
            monitoring_type="invalid_type"
        )

def test_data_persistence(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test persistence of monitoring results"""
    tool = ResourceMonitor(
        project_id="PROJ006",
        monitoring_type="efficiency"
    )
    
    result = tool.run()
    
    # Verify monitoring results were stored
    stored_results = mock_duckdb_connection.execute(
        "SELECT * FROM resource_monitoring WHERE project_id = 'PROJ006'"
    ).fetchall()
    assert len(stored_results) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 