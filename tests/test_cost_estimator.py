import pytest
from cost_analysis_agent.tools.cost_estimator import CostEstimator
from utils.error_handling import RetryError

def test_cost_estimation_success(mock_claude_client, mock_tavily_client, mock_duckdb_connection):
    """Test successful cost estimation"""
    test_specs = {
        "type": "commercial",
        "location": "New York City",
        "area": "50000 sqft",
        "materials": {
            "concrete": "5000 cubic yards",
            "steel": "500 tons"
        },
        "timeline": "18 months"
    }
    
    tool = CostEstimator(
        project_specs=test_specs,
        estimate_type="detailed"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_market_rate_lookup(mock_claude_client, mock_tavily_client, mock_duckdb_connection):
    """Test market rate research functionality"""
    test_specs = {
        "type": "residential",
        "location": "Los Angeles",
        "area": "2500 sqft",
        "materials": {
            "lumber": "20000 board feet",
            "concrete": "100 cubic yards"
        }
    }
    
    tool = CostEstimator(
        project_specs=test_specs,
        estimate_type="initial"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_change_order_estimation(mock_claude_client, mock_tavily_client, mock_duckdb_connection):
    """Test change order cost estimation"""
    test_specs = {
        "type": "industrial",
        "location": "Chicago",
        "change_details": {
            "additional_steel": "50 tons",
            "modified_timeline": "+2 months"
        }
    }
    
    tool = CostEstimator(
        project_specs=test_specs,
        estimate_type="change_order"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_api_failure_handling(mock_duckdb_connection):
    """Test handling of API failures"""
    class FailingTavilyClient:
        def search(self, *args, **kwargs):
            raise Exception("Market rate lookup failed")
    
    test_specs = {
        "type": "commercial",
        "location": "Miami",
        "area": "10000 sqft"
    }
    
    tool = CostEstimator(
        project_specs=test_specs,
        estimate_type="detailed"
    )
    
    with pytest.raises(RetryError):
        tool.run()

def test_invalid_project_specs():
    """Test validation of project specifications"""
    # Test missing required fields
    with pytest.raises(ValueError):
        CostEstimator(
            project_specs={},  # Empty specs
            estimate_type="detailed"
        )
    
    # Test invalid estimate type
    with pytest.raises(ValueError):
        CostEstimator(
            project_specs={"type": "commercial", "location": "Seattle"},
            estimate_type="invalid_type"
        )

def test_data_persistence(mock_claude_client, mock_tavily_client, mock_duckdb_connection):
    """Test storage of cost estimates"""
    test_specs = {
        "type": "commercial",
        "location": "Boston",
        "area": "30000 sqft",
        "materials": {
            "concrete": "3000 cubic yards"
        }
    }
    
    tool = CostEstimator(
        project_specs=test_specs,
        estimate_type="detailed"
    )
    
    result = tool.run()
    
    # Verify estimate was stored
    assert isinstance(result, str)
    assert len(result) > 0

def test_rate_limiting(mock_claude_client, mock_tavily_client, mock_duckdb_connection):
    """Test rate limiting for API calls"""
    test_specs = {
        "type": "residential",
        "location": "Denver",
        "area": "3000 sqft"
    }
    
    tool = CostEstimator(
        project_specs=test_specs,
        estimate_type="initial"
    )
    
    # Make multiple rapid requests
    start_time = pytest.helpers.time.time()
    for _ in range(3):
        tool.run()
    end_time = pytest.helpers.time.time()
    
    # Verify rate limiting worked
    assert end_time - start_time >= 0.6  # Minimum time for rate-limited requests

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 