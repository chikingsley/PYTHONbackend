from agency_swarm import Agent
from agency_swarm.tools import BaseTool, CodeInterpreter
from pydantic import Field, BaseModel
from typing import Dict, List, Any
import duckdb
import redis
import os
import json

class Task(BaseModel):
    task_id: str
    agent: str
    priority: int
    status: str
    metadata: Dict[str, Any]

class AssignTask(BaseTool):
    """Assign a task to another agent"""
    task: Dict[str, Any] = Field(..., description="Task details")
    agent: str = Field(..., description="Agent to assign the task to")
    priority: int = Field(default=1, description="Task priority (1-5)")

    def run(self):
        task_id = self.generate_task_id()
        task = Task(
            task_id=task_id,
            agent=self.agent,
            priority=self.priority,
            status="assigned",
            metadata=self.task
        )
        
        # Store task in DuckDB
        self.db.execute("""
            INSERT INTO tasks 
            (task_id, agent, priority, status, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (task_id, self.agent, self.priority, "assigned", task.metadata))
        
        # Publish task to Redis
        self.redis.publish(
            f"agent_tasks_{self.agent}",
            json.dumps(task.dict())
        )
        
        return f"Task {task_id} assigned to {self.agent}"

class GetTaskStatus(BaseTool):
    """Get the status of a task"""
    task_id: str = Field(..., description="Task ID to check")

    def run(self):
        status = self.db.execute("""
            SELECT status, metadata 
            FROM tasks 
            WHERE task_id = ?
        """, (self.task_id,)).fetchone()
        
        if not status:
            return f"Task {self.task_id} not found"
            
        return {
            "task_id": self.task_id,
            "status": status[0],
            "metadata": status[1]
        }

class UpdateWorkflow(BaseTool):
    """Update project workflow status"""
    project_id: str = Field(..., description="Project ID")
    status_update: Dict[str, Any] = Field(..., description="Status update details")

    def run(self):
        self.db.execute("""
            INSERT INTO workflow_status 
            (project_id, status, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (self.project_id, self.status_update))
        
        # Notify relevant agents through Redis
        self.redis.publish(
            f"project_updates_{self.project_id}",
            json.dumps(self.status_update)
        )
        
        return f"Workflow updated for project {self.project_id}"

class ProjectOrchestrationAgent(Agent):
    def __init__(self, **kwargs):
        # Initialize DuckDB
        self.db = duckdb.connect('orchestration.db')
        self.setup_database()
        
        # Initialize Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = redis.from_url(redis_url)
        
        # Add tools
        tools = kwargs.get('tools', []) + [
            AssignTask,
            GetTaskStatus,
            UpdateWorkflow,
            CodeInterpreter
        ]
        
        super().__init__(
            name="Project Orchestration Agent",
            description="I coordinate the construction project planning process and manage agent interactions.",
            instructions="./project_orchestration_agent/instructions.md",
            tools=tools,
            **kwargs
        )

    def setup_database(self):
        """Initialize DuckDB tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id VARCHAR PRIMARY KEY,
                agent VARCHAR,
                priority INTEGER,
                status VARCHAR,
                metadata JSON,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS workflow_status (
                status_id INTEGER PRIMARY KEY,
                project_id VARCHAR,
                status JSON,
                timestamp TIMESTAMP
            );
        """)
