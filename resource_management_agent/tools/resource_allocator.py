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
DUCKDB_PATH = "resource_store.db"

class ResourceAllocator(BaseTool):
    """
    Manages and allocates resources across construction projects, handling scheduling,
    availability, and conflict resolution.
    """
    
    resource_request: dict = Field(
        ..., 
        description="Resource request details including type, quantity, duration, and project"
    )
    
    priority_level: str = Field(
        ..., 
        description="Priority level of the request (e.g., 'high', 'medium', 'low')"
    )

    def run(self):
        """
        Allocates resources based on availability and project requirements.
        """
        try:
            # Initialize connections
            db = duckdb.connect(DUCKDB_PATH)
            claude = anthropic.Client(api_key=CLAUDE_API_KEY)
            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
            
            # Get current resource availability from Redis
            available_resources = json.loads(
                redis_client.get("resource_availability") or "{}"
            )
            
            # Get existing allocations from DuckDB
            current_allocations = db.execute("""
                SELECT * FROM resource_allocations 
                WHERE end_date >= CURRENT_DATE
            """).fetchall()
            
            # Generate allocation plan using Claude
            prompt = f"""
            Create a resource allocation plan considering:
            
            Resource Request:
            {self.resource_request}
            
            Priority Level: {self.priority_level}
            
            Available Resources:
            {available_resources}
            
            Current Allocations:
            {current_allocations}
            
            Please provide:
            1. Resource allocation decision
            2. Scheduling details
            3. Conflict resolution if needed
            4. Alternative recommendations
            5. Risk assessment
            """
            
            message = claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            allocation_plan = message.content
            
            # Store allocation in DuckDB
            db.execute("""
                INSERT INTO resource_allocations 
                (request_details, priority, allocation_plan)
                VALUES (?, ?, ?)
            """, (str(self.resource_request), self.priority_level, allocation_plan))
            
            # Update Redis with new allocation
            allocation_data = {
                "type": self.resource_request.get("type"),
                "quantity": self.resource_request.get("quantity"),
                "status": "allocated"
            }
            
            redis_client.publish(
                "resource_updates",
                json.dumps(allocation_data)
            )
            
            return allocation_plan
            
        except Exception as e:
            return f"Error allocating resources: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    test_request = {
        "type": "heavy_equipment",
        "quantity": 2,
        "equipment": "excavator",
        "duration": "2 weeks",
        "project": "Site A Foundation",
        "start_date": "2024-03-15"
    }
    
    tool = ResourceAllocator(
        resource_request=test_request,
        priority_level="high"
    )
    print(tool.run()) 