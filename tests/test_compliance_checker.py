import pytest
from compliance_agent.tools.compliance_checker import ComplianceChecker
from utils.error_handling import RetryError

def test_compliance_check_success(mock_claude_client, mock_tavily_client, mock_duckdb_connection, mock_redis_client):
    """Test successful compliance check"""
    test_project = {
        "location": "New York City",
        "type": "commercial",
        "scope": "New construction",
        "specifications": {
            "height": "120 feet",
            "area": "50000 sqft",
            "occupancy": "Business"
        },
        "embedding": [0.1] * 1536
    }
    
    tool = ComplianceChecker(
        project_details=test_project,
        check_type="building_code"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_compliance_check_api_retry(mock_duckdb_connection, mock_redis_client):
    """Test retry mechanism for API failures"""
    class FailingTavilyClient:
        fail_count = 0
        def search(self, *args, **kwargs):
            if FailingTavilyClient.fail_count < 2:
                FailingTavilyClient.fail_count += 1
                raise Exception("API Error")
            return [{"content": "Success after retry"}]
    
    test_project = {
        "location": "Chicago",
        "type": "residential",
        "scope": "Renovation",
        "embedding": [0.1] * 1536
    }
    
    tool = ComplianceChecker(
        project_details=test_project,
        check_type="permits"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_compliance_check_data_validation():
    """Test input data validation"""
    # Test missing location
    with pytest.raises(ValueError):
        ComplianceChecker(
            project_details={
                "type": "commercial",
                "embedding": [0.1] * 1536
            },
            check_type="building_code"
        )
    
    # Test invalid check type
    with pytest.raises(ValueError):
        ComplianceChecker(
            project_details={
                "location": "Miami",
                "type": "commercial",
                "embedding": [0.1] * 1536
            },
            check_type="invalid_type"
        )

def test_compliance_check_rate_limiting(mock_claude_client, mock_tavily_client, mock_duckdb_connection, mock_redis_client):
    """Test rate limiting functionality"""
    test_project = {
        "location": "Los Angeles",
        "type": "industrial",
        "scope": "New construction",
        "embedding": [0.1] * 1536
    }
    
    tool = ComplianceChecker(
        project_details=test_project,
        check_type="safety"
    )
    
    # Make multiple rapid requests
    start_time = pytest.helpers.time.time()
    results = []
    for _ in range(3):
        result = tool.run()
        results.append(result)
    end_time = pytest.helpers.time.time()
    
    # Verify rate limiting worked
    assert end_time - start_time >= 0.6  # Minimum time for rate-limited requests
    assert all(isinstance(r, str) for r in results)
    assert all(len(r) > 0 for r in results)

def test_compliance_check_database_error(mock_claude_client, mock_tavily_client):
    """Test database error handling"""
    class FailingDuckDB:
        def execute(self, *args, **kwargs):
            raise Exception("Database connection error")
    
    test_project = {
        "location": "Seattle",
        "type": "commercial",
        "embedding": [0.1] * 1536
    }
    
    tool = ComplianceChecker(
        project_details=test_project,
        check_type="zoning"
    )
    
    with pytest.raises(Exception) as exc_info:
        tool.run()
    assert "Database connection error" in str(exc_info.value)

def test_compliance_check_milvus_error(mock_claude_client, mock_tavily_client, mock_duckdb_connection):
    """Test Milvus connection error handling"""
    class FailingMilvus:
        def search(self, *args, **kwargs):
            raise Exception("Milvus connection error")
    
    test_project = {
        "location": "Boston",
        "type": "residential",
        "embedding": [0.1] * 1536
    }
    
    tool = ComplianceChecker(
        project_details=test_project,
        check_type="environmental"
    )
    
    with pytest.raises(RetryError):
        tool.run()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])