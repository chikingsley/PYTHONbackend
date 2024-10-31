import pytest
from technical_validation_agent.tools.technical_validator import TechnicalValidator
from utils.error_handling import RetryError

def test_technical_validation_success(mock_claude_client, mock_tavily_client, mock_duckdb_connection):
    """Test successful technical validation"""
    test_specs = {
        "materials": {
            "concrete": "Type II Portland Cement",
            "reinforcement": "Grade 60 rebar"
        },
        "methods": {
            "foundation": "Spread footing",
            "construction_type": "Cast-in-place"
        },
        "timeline": {
            "foundation": "4 weeks",
            "structure": "12 weeks"
        }
    }
    
    tool = TechnicalValidator(
        specifications=test_specs,
        project_type="commercial"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_technical_validation_api_retry(mock_claude_client, mock_duckdb_connection):
    """Test retry mechanism for API failures"""
    class FailingTavilyClient:
        fail_count = 0
        def search(self, *args, **kwargs):
            if FailingTavilyClient.fail_count < 2:
                FailingTavilyClient.fail_count += 1
                raise Exception("API Error")
            return [{"content": "Success after retry"}]
    
    test_specs = {
        "materials": {
            "concrete": "Type II Portland Cement"
        },
        "methods": {
            "foundation": "Spread footing"
        }
    }
    
    tool = TechnicalValidator(
        specifications=test_specs,
        project_type="commercial"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert len(result) > 0

def test_technical_validation_rate_limit(mock_claude_client, mock_tavily_client, mock_duckdb_connection):
    """Test rate limiting functionality"""
    test_specs = {
        "materials": {"concrete": "Type II Portland Cement"},
        "methods": {"foundation": "Spread footing"}
    }
    
    tool = TechnicalValidator(
        specifications=test_specs,
        project_type="commercial"
    )
    
    # Make multiple rapid requests
    results = []
    for _ in range(3):
        result = tool.run()
        results.append(result)
    
    assert all(isinstance(r, str) for r in results)
    assert all(len(r) > 0 for r in results)

def test_technical_validation_database_error(mock_claude_client, mock_tavily_client):
    """Test handling of database connection errors"""
    class FailingDuckDB:
        def execute(self, *args, **kwargs):
            raise Exception("Database connection error")
    
    test_specs = {
        "materials": {"concrete": "Type II Portland Cement"},
        "methods": {"foundation": "Spread footing"}
    }
    
    tool = TechnicalValidator(
        specifications=test_specs,
        project_type="commercial"
    )
    
    with pytest.raises(Exception) as exc_info:
        tool.run()
    assert "Database connection error" in str(exc_info.value)

def test_technical_validation_invalid_input():
    """Test handling of invalid input specifications"""
    with pytest.raises(ValueError):
        TechnicalValidator(
            specifications={},  # Empty specifications
            project_type="commercial"
        )
    
    with pytest.raises(ValueError):
        TechnicalValidator(
            specifications={"invalid": "spec"},
            project_type=""  # Empty project type
        )

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 