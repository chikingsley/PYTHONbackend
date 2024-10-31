import pytest
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load test environment variables
load_dotenv(".env.test")

@pytest.fixture
def mock_claude_client():
    """Mock Claude API client"""
    class MockClaude:
        def messages(self):
            class Messages:
                def create(self, *args, **kwargs):
                    class Response:
                        content = "Mocked response content"
                    return Response()
            return Messages()
    return MockClaude()

@pytest.fixture
def mock_tavily_client():
    """Mock Tavily API client"""
    class MockTavily:
        def search(self, *args, **kwargs):
            return [{"content": "Mocked search result"}]
    return MockTavily()

@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    class MockRedis:
        def __init__(self):
            self.data = {}
        
        def get(self, key):
            return self.data.get(key)
        
        def set(self, key, value):
            self.data[key] = value
        
        def publish(self, channel, message):
            pass
    return MockRedis()

@pytest.fixture
def mock_duckdb_connection():
    """Mock DuckDB connection"""
    class MockDuckDB:
        def execute(self, query, params=None):
            pass
        
        def fetchall(self):
            return []
    return MockDuckDB() 