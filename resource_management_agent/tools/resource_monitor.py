from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import duckdb
import redis
import anthropic
import json
from datetime import datetime

load_dotenv()

# Global variables
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
DUCKDB_PATH = "resource_store.db"

class ResourceMonitor(BaseTool):
    """
    Monitors resource utilization, tracks efficiency, and identifies potential conflicts
    or optimization opportunities.
    """
    
    project_id: str = Field(
        ..., 
        description="ID of the project to monitor resources for"
    )
    
    monitoring_type: str = Field(
        ..., 
        description="Type of monitoring (e.g., 'utilization', 'efficiency', 'conflicts')"
    )

    def run(self):
        """
        Monitors and analyzes resource usage and performance.
        """
        try:
            # Initialize connections
            db = duckdb.connect(DUCKDB_PATH)
            claude = anthropic.Client(api_key=CLAUDE_API_KEY)
            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
            
            # Get current resource status
            resource_status = json.loads(
                redis_client.get(f"project_resources:{self.project_id}") or "{}"
            )
            
            # Get historical utilization data
            utilization_data = db.execute("""
                SELECT * FROM resource_utilization 
                WHERE project_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 100
            """, [self.project_id]).fetchall()
            
            # Analyze using Claude
            prompt = f"""
            Analyze resource utilization for:
            
            Project ID: {self.project_id}
            Monitoring Type: {self.monitoring_type}
            
            Current Status:
            {resource_status}
            
            Historical Data:
            {utilization_data}
            
            Please provide:
            1. Utilization analysis
            2. Efficiency metrics
            3. Identified conflicts
            4. Optimization opportunities
            5. Risk factors
            6. Recommendations
            """
            
            message = claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            analysis_results = message.content
            
            # Store analysis
            db.execute("""
                INSERT INTO resource_monitoring 
                (project_id, monitoring_type, results, timestamp)
                VALUES (?, ?, ?, ?)
            """, (self.project_id, self.monitoring_type, analysis_results, datetime.now()))
            
            # Publish alerts if needed
            if "ALERT" in analysis_results:
                alert_data = {
                    "project_id": self.project_id,
                    "type": "resource_alert",
                    "details": analysis_results
                }
                redis_client.publish("resource_alerts", json.dumps(alert_data))
            
            return analysis_results
            
        except Exception as e:
            return f"Error monitoring resources: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = ResourceMonitor(
        project_id="PROJ001",
        monitoring_type="utilization"
    )
    print(tool.run()) 