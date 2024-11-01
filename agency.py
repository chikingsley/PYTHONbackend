from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from agency_swarm import Agency
from typing import Dict, Optional
import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Keep existing agent imports and initialization
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
doc_agent = DocumentCreationAgent()
tech_agent = TechnicalValidationAgent()
compliance_agent = ComplianceAgent()
cost_agent = CostAnalysisAgent()
orchestration_agent = ProjectOrchestrationAgent()
resource_agent = ResourceManagementAgent()

# Create agency with existing communication flows
construction_agency = Agency(
    [
        orchestration_agent,
        [orchestration_agent, doc_agent],
        [orchestration_agent, tech_agent],
        [orchestration_agent, compliance_agent],
        [orchestration_agent, cost_agent],
        [orchestration_agent, resource_agent],
        [doc_agent, tech_agent],
        [doc_agent, compliance_agent],
        [doc_agent, cost_agent],
        [tech_agent, compliance_agent],
        [tech_agent, resource_agent],
        [compliance_agent, resource_agent],
        [cost_agent, resource_agent],
    ],
    shared_instructions="agency_manifesto.md",
    temperature=0.2,
    max_prompt_tokens=4000
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
        """Broadcast progress updates to frontend"""
        for agent_id, websocket in self.active_connections.items():
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

@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            # Start conversation flow with progress updates
            if data["target_agent"] == "orchestration-agent":
                # Initial requirements gathering
                await manager.broadcast_progress(
                    data["source_agent"],
                    "orchestration-agent",
                    20,
                    "Gathering project requirements..."
                )
                
                response = construction_agency.get_completion(
                    message=data["message"],
                    recipient_agent="orchestration-agent"
                )
                
                # Process requirements with technical agent
                await manager.broadcast_progress(
                    "orchestration-agent",
                    "technical-agent",
                    40,
                    "Validating technical specifications..."
                )
                
                tech_response = construction_agency.get_completion(
                    message=response,
                    recipient_agent="technical-agent"
                )
                
                # Compliance check
                await manager.broadcast_progress(
                    "technical-agent",
                    "compliance-agent",
                    60,
                    "Checking regulatory compliance..."
                )
                
                compliance_response = construction_agency.get_completion(
                    message=tech_response,
                    recipient_agent="compliance-agent"
                )
                
                # Cost analysis
                await manager.broadcast_progress(
                    "compliance-agent",
                    "cost-agent",
                    80,
                    "Analyzing costs and budget..."
                )
                
                cost_response = construction_agency.get_completion(
                    message=compliance_response,
                    recipient_agent="cost-agent"
                )
                
                # Generate documents
                await manager.broadcast_progress(
                    "cost-agent",
                    "document-agent",
                    90,
                    "Generating project documents..."
                )
                
                doc_response = construction_agency.get_completion(
                    message=cost_response,
                    recipient_agent="document-agent"
                )
                
                # Final resource allocation
                await manager.broadcast_progress(
                    "document-agent",
                    "resource-agent",
                    100,
                    "Allocating project resources..."
                )
                
                final_response = construction_agency.get_completion(
                    message=doc_response,
                    recipient_agent="resource-agent"
                )
                
                # Send completion status
                await manager.broadcast_to_agent(agent_id, {
                    "type": "response",
                    "data": {
                        "status": "complete",
                        "message": "Project planning completed"
                    },
                    "source": "resource-agent",
                    "target": data["source_agent"]
                })
            
            else:
                # Handle direct agent-to-agent communication
                response = construction_agency.get_completion(
                    message=data["message"],
                    recipient_agent=data["target_agent"]
                )
                
                await manager.broadcast_to_agent(agent_id, {
                    "type": "response",
                    "data": response,
                    "source": data["source_agent"],
                    "target": data["target_agent"]
                })
                
    except WebSocketDisconnect:
        manager.disconnect(agent_id)
    except Exception as e:
        print(f"Error: {str(e)}")
        manager.disconnect(agent_id)

@app.get("/api/agents")
async def get_agents():
    return {
        "agents": [
            {"id": "document", "name": "Document Creation Agent"},
            {"id": "technical", "name": "Technical Validation Agent"},
            {"id": "compliance", "name": "Compliance Agent"},
            {"id": "cost", "name": "Cost Analysis Agent"},
            {"id": "orchestration", "name": "Project Orchestration Agent"},
            {"id": "resource", "name": "Resource Management Agent"}
        ],
        "flows": construction_agency.agency_chart
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
