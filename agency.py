from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from agency_swarm import Agency, Agent
from agency_swarm.tools import BaseTool
from typing import Dict, Optional, List, AsyncGenerator
import asyncio
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import redis
from pymilvus import connections
import duckdb

# Load environment variables
load_dotenv()

# Define base tools that all agents can use
class SendMessage(BaseTool):
    """Use this tool to send a message to another agent"""
    message: str = Field(..., description="The message to send")
    recipient: str = Field(..., description="The agent to send the message to")

    def run(self):
        return f"Message sent to {self.recipient}: {self.message}"

class GetResponse(BaseTool):
    """Use this tool to get a response from another agent"""
    agent_id: str = Field(..., description="The agent to get the response from")

    def run(self):
        response = self._shared_state.get(f"response_{self.agent_id}")
        if not response:
            return "No response available yet"
        return response

# Keep existing agent imports but initialize with tools
from document_creation_agent.document_creation_agent import DocumentCreationAgent
from technical_validation_agent.technical_validation_agent import TechnicalValidationAgent
from compliance_agent.compliance_agent import ComplianceAgent
from cost_analysis_agent.cost_analysis_agent import CostAnalysisAgent
from project_orchestration_agent.project_orchestration_agent import ProjectOrchestrationAgent
from resource_management_agent.resource_management_agent import ResourceManagementAgent

# Initialize FastAPI
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider restricting this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connections
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))  # Added default value
# Get DuckDB path from environment variables
duckdb_path = os.getenv('DUCKDB_PATH', '/Users/simonpeacocks/Documents/GitHub/fullapp/PYTHONbackend/construction_db.db')
duckdb_conn = duckdb.connect(duckdb_path)
# Initialize Milvus
try:
    connections.connect(
        host=os.getenv('MILVUS_HOST', 'localhost'),  # Added default value
        port=os.getenv('MILVUS_PORT', '19530')  # Added default value
    )
except Exception as e:
    print(f"Warning: Failed to connect to Milvus: {str(e)}")

# Base configuration for all agents
agent_config = {
    "model": os.getenv('AI_MODEL', 'gpt-4-1106-preview'),
    "temperature": float(os.getenv('TEMPERATURE', 0.2)),
    "max_tokens": int(os.getenv('MAX_TOKENS', 4000)),
    "tools": [SendMessage, GetResponse],  # Add base tools to all agents
    "redis_client": redis_client,
    "duckdb_conn": duckdb_conn
}

# Initialize agents with shared config and specific tools
doc_agent = DocumentCreationAgent(
    name="Document Creation Agent",
    description="Creates and manages construction documentation",
    instructions="./document_creation_agent/instructions.md",
    **agent_config
)

tech_agent = TechnicalValidationAgent(
    name="Technical Validation Agent",
    description="Validates technical aspects and specifications",
    instructions="./technical_validation_agent/instructions.md",
    **agent_config
)

compliance_agent = ComplianceAgent(
    name="Compliance Agent",
    description="Ensures regulatory compliance",
    instructions="./compliance_agent/instructions.md",
    **agent_config
)

cost_agent = CostAnalysisAgent(
    name="Cost Analysis Agent",
    description="Analyzes costs and validates budgets",
    instructions="./cost_analysis_agent/instructions.md",
    **agent_config
)

orchestration_agent = ProjectOrchestrationAgent(
    name="Project Orchestration Agent",
    description="Coordinates project workflow and agent communication",
    instructions="./project_orchestration_agent/instructions.md",
    **agent_config
)

resource_agent = ResourceManagementAgent(
    name="Resource Management Agent",
    description="Manages project resources and allocations",
    instructions="./resource_management_agent/instructions.md",
    **agent_config
)

# Create agency with proper flow and configuration
construction_agency = Agency(
    [
        orchestration_agent,  # Entry point for user communication
        [orchestration_agent, tech_agent],
        [orchestration_agent, compliance_agent],
        [orchestration_agent, cost_agent],
        [orchestration_agent, resource_agent],
        [tech_agent, compliance_agent],
        [tech_agent, resource_agent],
        [compliance_agent, resource_agent],
        [cost_agent, resource_agent],
        # Document agent comes last as it needs info from others
        [orchestration_agent, doc_agent],
        [doc_agent, tech_agent],
        [doc_agent, compliance_agent],
        [doc_agent, cost_agent],
    ],
    shared_instructions="agency_manifesto.md",
    temperature=0.2,
    max_prompt_tokens=25000,
    async_mode='threading',  # Enable async communication
    shared_files='shared_files'  # For sharing resources between agents
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, agent_id: str):
        await websocket.accept()
        self.active_connections[agent_id] = websocket

    def disconnect(self, agent_id: str):
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]

    async def broadcast_to_agent(self, agent_id: str, message: dict):
        if agent_id in self.active_connections:
            await self.active_connections[agent_id].send_json(message)

    async def broadcast_progress(self, source: str, target: str, progress: int, message: str):
        for websocket in self.active_connections.values():
            await websocket.send_json({
                "type": "progress",
                "source": source,
                "target": target,
                "data": {
                    "progress": progress,
                    "message": message
                }
            })

manager = ConnectionManager()

# Add this function for streaming responses
async def stream_completion(message: str, recipient_agent: Agent) -> AsyncGenerator[str, None]:
    """Stream the completion response"""
    try:
        response_stream = construction_agency.get_completion(
            message=message,
            recipient_agent=recipient_agent,
            stream=True  # Enable streaming
        )
        
        async for response_chunk in response_stream:
            if response_chunk:
                yield response_chunk
    except Exception as e:
        print(f"Error in stream_completion: {str(e)}")
        yield f"Error: {str(e)}"

# Modify your websocket endpoint to handle streaming
@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    print(f"New connection request from agent_id: {agent_id}")
    await manager.connect(websocket, agent_id)
    try:
        while True:
            print(f"Waiting for message from {agent_id}...")
            try:
                data = await websocket.receive_json()
                print(f"Received message data:", data)
                
                if "target_agent" not in data or "message" not in data or "source_agent" not in data:
                    raise ValueError("Missing required fields in message")
                
                if data["target_agent"] == "orchestration-agent":
                    print("Starting orchestration flow...")
                    try:
                        # Send initial progress
                        await manager.broadcast_progress(
                            data["source_agent"],
                            "orchestration-agent",
                            20,
                            "Gathering project requirements..."
                        )
                        
                        # Stream the response
                        async for response_chunk in stream_completion(
                            message=data["message"],
                            recipient_agent=orchestration_agent
                        ):
                            # Send each chunk to the frontend
                            chunk_data = {
                                "type": "stream",
                                "data": {
                                    "name": "Orchestration Agent",
                                    "type": "orchestration",
                                    "status": "processing",
                                    "message": response_chunk,
                                    "currentTask": "Processing construction project request",
                                    "progress": 25
                                },
                                "source": "orchestration-agent",
                                "target": data["source_agent"]
                            }
                            
                            await manager.broadcast_to_agent(agent_id, chunk_data)
                        
                        # Send completion message
                        final_response = {
                            "type": "response",
                            "data": {
                                "name": "Orchestration Agent",
                                "type": "orchestration",
                                "status": "complete",
                                "message": "Task completed",
                                "progress": 100
                            },
                            "source": "orchestration-agent",
                            "target": data["source_agent"]
                        }
                        
                        await manager.broadcast_to_agent(agent_id, final_response)
                        
                    except Exception as e:
                        print(f"Error in orchestration flow: {str(e)}")
                        error_response = {
                            "type": "error",
                            "data": {
                                "name": "Orchestration Agent",
                                "type": "orchestration",
                                "status": "error",
                                "message": f"Error processing request: {str(e)}",
                                "error": str(e)
                            },
                            "source": "orchestration-agent",
                            "target": data["source_agent"]
                        }
                        await manager.broadcast_to_agent(agent_id, error_response)
                        
            except json.JSONDecodeError:
                print("Error: Invalid JSON received")
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "name": "System",
                        "type": "error",
                        "message": "Invalid JSON format"
                    }
                })
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for agent_id: {agent_id}")
        manager.disconnect(agent_id)
    except Exception as e:
        print(f"Error in websocket handler: {str(e)}")
        manager.disconnect(agent_id)
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
