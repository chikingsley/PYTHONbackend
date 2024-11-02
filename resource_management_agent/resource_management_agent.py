from agency_swarm import Agent
from agency_swarm.tools import BaseTool, CodeInterpreter
from pydantic import Field, BaseModel
from typing import Dict, List, Any
import duckdb
import redis
import os
import json
from datetime import datetime

class Resource(BaseModel):
    resource_id: str
    type: str
    quantity: int
    availability: Dict[str, Any]
    metadata: Dict[str, Any]

class AllocateResources(BaseTool):
    """Allocate resources to project tasks"""
    task: str = Field(..., description="The task requiring resources")
    requirements: Dict[str, Any] = Field(..., description="Resource requirements")
    duration: str = Field(..., description="Expected duration of resource need")

    def run(self):
        # Check real-time availability in Redis
        available_resources = self.redis.hgetall("resource_availability")
        
        allocation = self.calculate_allocation(
            self.requirements,
            available_resources,
            self.duration
        )
        
        if allocation["success"]:
            # Update availability in Redis
            self.update_resource_availability(allocation["allocated"])
            
            # Store allocation in DuckDB
            self.db.execute("""
                INSERT INTO resource_allocations 
                (task_id, resources, duration, start_date)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (self.task, allocation["allocated"], self.duration))
        
        return allocation

    def calculate_allocation(self, requirements, available, duration):
        allocated = {}
        for resource_type, quantity in requirements.items():
            if resource_type not in available or available[resource_type] < quantity:
                return {"success": False, "error": f"Insufficient {resource_type}"}
            allocated[resource_type] = quantity
        return {"success": True, "allocated": allocated}

class CheckAvailability(BaseTool):
    """Check resource availability"""
    resource_type: str = Field(..., description="Type of resource needed")
    timeframe: str = Field(..., description="When the resource is needed")
    quantity: int = Field(..., description="Amount of resource needed")

    def run(self):
        # Check current availability in Redis
        current = self.redis.hget("resource_availability", self.resource_type)
        
        # Get future allocations from DuckDB
        future_allocations = self.db.execute("""
            SELECT resources, duration, start_date
            FROM resource_allocations
            WHERE resources->? IS NOT NULL
            AND start_date <= ?
        """, (self.resource_type, self.timeframe)).fetchall()
        
        availability = self.calculate_availability(
            current,
            future_allocations,
            self.quantity
        )
        
        return availability

class ManageConflicts(BaseTool):
    """Handle resource allocation conflicts"""
    conflict_details: Dict[str, Any] = Field(..., description="Details of the resource conflict")
    priority: int = Field(default=1, description="Priority of the request (1-5)")

    def run(self):
        # Store conflict in DuckDB
        self.db.execute("""
            INSERT INTO resource_conflicts 
            (details, priority, status, created_at)
            VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
        """, (self.conflict_details, self.priority))
        
        # Notify through Redis
        self.redis.publish(
            "resource_conflicts",
            json.dumps({
                "type": "conflict",
                "priority": self.priority,
                "details": self.conflict_details
            })
        )
        
        return "Conflict logged and notifications sent"

class ResourceManagementAgent(Agent):
    def __init__(self, **kwargs):
        # Initialize DuckDB
        self.db = duckdb.connect('resource_management.db')
        self.setup_database()
        
        # Initialize Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = redis.from_url(redis_url)
        
        # Add tools
        tools = kwargs.get('tools', []) + [
            AllocateResources,
            CheckAvailability,
            ManageConflicts,
            CodeInterpreter
        ]
        
        super().__init__(
            name="Resource Management Agent",
            description="I manage and optimize resource allocation for construction projects.",
            instructions="./resource_management_agent/instructions.md",
            tools=tools,
            **kwargs
        )

    def setup_database(self):
        """Initialize DuckDB tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS resource_allocations (
                allocation_id INTEGER PRIMARY KEY,
                task_id VARCHAR,
                resources JSON,
                duration VARCHAR,
                start_date TIMESTAMP,
                status VARCHAR DEFAULT 'active'
            );
            
            CREATE TABLE IF NOT EXISTS resource_conflicts (
                conflict_id INTEGER PRIMARY KEY,
                details JSON,
                priority INTEGER,
                status VARCHAR,
                created_at TIMESTAMP,
                resolved_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS resource_utilization (
                utilization_id INTEGER PRIMARY KEY,
                resource_type VARCHAR,
                quantity INTEGER,
                timestamp TIMESTAMP,
                project_id VARCHAR
            );
        """)

    def initialize_redis_resources(self):
        """Initialize default resource availability in Redis"""
        default_resources = {
            "workers": 100,
            "equipment": 50,
            "vehicles": 30,
            "materials": 1000
        }
        
        for resource, quantity in default_resources.items():
            self.redis.hset("resource_availability", resource, quantity) 