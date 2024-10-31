from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import duckdb
import redis
import anthropic
import json

load_dotenv()

# Global variables
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
DUCKDB_PATH = "workflow_store.db"

class WorkflowCoordinator(BaseTool):
    """
    Coordinates workflow between different agents and manages task execution sequence.
    """
    
    task_details: dict = Field(
        ..., 
        description="Details of the task to be coordinated including type, priority, and dependencies"
    )
    
    workflow_type: str = Field(
        ..., 
        description="Type of workflow (e.g., 'document_review', 'compliance_check', 'cost_estimation')"
    )

    def run(self):
        """
        Coordinates task execution and manages workflow between agents.
        """
        try:
            # Initialize connections
            db = duckdb.connect(DUCKDB_PATH)
            claude = anthropic.Client(api_key=CLAUDE_API_KEY)
            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
            
            # Generate workflow plan using Claude
            prompt = f"""
            Create a detailed workflow plan for the following task:
            
            Task Details:
            {self.task_details}
            
            Workflow Type: {self.workflow_type}
            
            Please provide:
            1. Required agent sequence
            2. Task dependencies
            3. Priority levels
            4. Expected timeline
            5. Communication points
            6. Decision gates
            """
            
            message = claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            workflow_plan = message.content
            
            # Store workflow in DuckDB
            db.execute("""
                INSERT INTO workflows (type, details, plan)
                VALUES (?, ?, ?)
            """, (self.workflow_type, str(self.task_details), workflow_plan))
            
            # Publish task assignments to Redis
            workflow_data = {
                "type": self.workflow_type,
                "details": self.task_details,
                "plan": workflow_plan,
                "status": "initiated"
            }
            
            redis_client.publish(
                "workflow_tasks",
                json.dumps(workflow_data)
            )
            
            return f"Workflow initiated: {workflow_plan}"
            
        except Exception as e:
            return f"Error coordinating workflow: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    test_task = {
        "type": "document_review",
        "priority": "high",
        "dependencies": ["technical_validation", "compliance_check"],
        "deadline": "2024-03-20"
    }
    
    tool = WorkflowCoordinator(
        task_details=test_task,
        workflow_type="document_review"
    )
    print(tool.run()) 