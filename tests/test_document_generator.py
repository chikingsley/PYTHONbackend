import pytest
from document_creation_agent.tools.document_generator import DocumentGenerator
from utils.error_handling import RetryError

def test_document_generation_success(mock_claude_client, mock_duckdb_connection):
    """Test successful document generation"""
    tool = DocumentGenerator(
        project_spec={
            "type": "residential",
            "scope": "New construction",
            "location": "New York",
            "embedding": [0.1] * 1536
        },
        document_type="contract"
    )
    
    result = tool.run()
    assert "Successfully generated contract document" in result

def test_document_generation_retry(mock_claude_client, mock_duckdb_connection):
    """Test retry mechanism for document generation"""
    class FailingClaudeClient:
        fail_count = 0
        def messages(self):
            class Messages:
                def create(self, *args, **kwargs):
                    if FailingClaudeClient.fail_count < 2:
                        FailingClaudeClient.fail_count += 1
                        raise Exception("API Error")
                    class Response:
                        content = "Success after retry"
                    return Response()
            return Messages()
    
    tool = DocumentGenerator(
        project_spec={
            "type": "residential",
            "scope": "New construction",
            "location": "New York",
            "embedding": [0.1] * 1536
        },
        document_type="contract"
    )
    
    result = tool.run()
    assert "Successfully generated contract document" in result

def test_document_generation_failure(mock_claude_client, mock_duckdb_connection):
    """Test complete failure of document generation"""
    class FailingClaudeClient:
        def messages(self):
            class Messages:
                def create(self, *args, **kwargs):
                    raise Exception("Permanent API Error")
            return Messages()
    
    tool = DocumentGenerator(
        project_spec={
            "type": "residential",
            "scope": "New construction",
            "location": "New York",
            "embedding": [0.1] * 1536
        },
        document_type="contract"
    )
    
    with pytest.raises(RetryError):
        tool.run() 