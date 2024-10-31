import pytest
import json
from project_orchestration_agent.tools.workflow_coordinator import WorkflowCoordinator
from utils.error_handling import RetryError

def test_workflow_coordination_success(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test successful workflow coordination"""
    test_task = {
        "type": "document_review",
        "priority": "high",
        "dependencies": ["technical_validation", "compliance_check"],
        "deadline": "2024-03-20",
        "project_id": "PROJ001",
        "stakeholders": ["architect", "engineer"]
    }
    
    tool = WorkflowCoordinator(
        task_details=test_task,
        workflow_type="document_review"
    )
    
    result = tool.run()
    assert isinstance(result, str)
    assert "Workflow initiated" in result

def test_workflow_task_assignment(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test task assignment and messaging"""
    test_task = {
        "type": "compliance_review",
        "priority": "medium",
        "assignee": "compliance_agent",
        "project_id": "PROJ002"
    }
    
    tool = WorkflowCoordinator(
        task_details=test_task,
        workflow_type="compliance_review"
    )
    
    result = tool.run()
    
    # Verify Redis message was published
    published_messages = mock_redis_client.published_messages
    assert len(published_messages) > 0
    assert "workflow_tasks" in published_messages[0]["channel"]
    
    # Verify message content
    message_data = json.loads(published_messages[0]["message"])
    assert message_data["type"] == "compliance_review"
    assert message_data["status"] == "initiated"

def test_workflow_dependency_handling(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test handling of task dependencies"""
    test_task = {
        "type": "final_approval",
        "priority": "high",
        "dependencies": [
            {"task": "technical_review", "status": "completed"},
            {"task": "compliance_check", "status": "pending"},
            {"task": "cost_validation", "status": "in_progress"}
        ]
    }
    
    tool = WorkflowCoordinator(
        task_details=test_task,
        workflow_type="approval_workflow"
    )
    
    result = tool.run()
    assert "pending dependencies" in result.lower()

def test_workflow_error_handling(mock_duckdb_connection, mock_redis_client):
    """Test handling of workflow errors"""
    class FailingClaudeClient:
        def messages(self):
            class Messages:
                def create(self, *args, **kwargs):
                    raise Exception("Workflow planning failed")
            return Messages()
    
    test_task = {
        "type": "resource_allocation",
        "priority": "medium"
    }
    
    tool = WorkflowCoordinator(
        task_details=test_task,
        workflow_type="resource_workflow"
    )
    
    with pytest.raises(RetryError):
        tool.run()

def test_workflow_data_validation():
    """Test validation of workflow data"""
    # Test missing required fields
    with pytest.raises(ValueError):
        WorkflowCoordinator(
            task_details={},  # Empty details
            workflow_type="document_review"
        )
    
    # Test invalid workflow type
    with pytest.raises(ValueError):
        WorkflowCoordinator(
            task_details={"type": "review", "priority": "high"},
            workflow_type="invalid_workflow"
        )

def test_workflow_persistence(mock_claude_client, mock_duckdb_connection, mock_redis_client):
    """Test workflow data storage"""
    test_task = {
        "type": "cost_review",
        "priority": "low",
        "project_id": "PROJ003",
        "deadline": "2024-04-01"
    }
    
    tool = WorkflowCoordinator(
        task_details=test_task,
        workflow_type="cost_workflow"
    )
    
    result = tool.run()
    
    # Verify workflow was stored in database
    stored_workflows = mock_duckdb_connection.execute(
        "SELECT * FROM workflows WHERE type = 'cost_workflow'"
    ).fetchall()
    assert len(stored_workflows) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 