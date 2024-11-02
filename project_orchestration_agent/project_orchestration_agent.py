from agency_swarm import Agent
from .tools.workflow_coordinator import WorkflowCoordinator
import json

class ProjectOrchestrationAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Project Orchestration Agent",
            description="Specialized agent responsible for coordinating workflows and managing communication between agents",
            instructions="./instructions.md",
            tools=[WorkflowCoordinator],
            temperature=0.2,
            max_prompt_tokens=4000,
        )
        
    def process_request(self, request: str) -> str:
        """Process incoming construction project requests"""
        # Load project specifications
        with open("project_orchestration_agent/project_spec.json", "r") as f:
            project_spec = json.load(f)
        
        # Extract key information from request
        request_summary = self.summarize_request(request)
        
        # Check if request matches project specifications
        if self.validate_request(request_summary, project_spec):
            # If valid, initiate workflow
            workflow_response = self.initiate_workflow(project_spec)
            return f"Request accepted. Initiating project workflow:\n{workflow_response}"
        else:
            # If not valid, request clarification
            return "Request does not match current project specifications. Please provide more details or update the specifications."
    
    def summarize_request(self, request: str) -> dict:
        """Summarize key points from construction request"""
        prompt = f"""
        Please summarize the key points from the following construction project request:
        
        {request}
        
        Provide a summary in the following JSON format:
        {{
            "project_type": "type of project",
            "scope": "high-level scope",
            "location": "project location",
            "key_requirements": ["requirement1", "requirement2", ...]
        }}
        """
        
        summary = self.complete(prompt)
        return json.loads(summary)
    
    def validate_request(self, request_summary: dict, project_spec: dict) -> bool:
        """Check if request matches project specifications"""
        if request_summary["project_type"] != project_spec["type"]:
            return False
        if request_summary["scope"] != project_spec["scope"]:
            return False
        if request_summary["location"] != project_spec["location"]:
            return False
        for req in request_summary["key_requirements"]:
            if req not in project_spec["requirements"]:
                return False
        return True
    
    def initiate_workflow(self, project_spec: dict) -> str:
        """Initiate project workflow based on specifications"""
        coordinator = WorkflowCoordinator(
            task_details=project_spec,
            workflow_type=project_spec["type"]  # Use the project type from specifications instead of hardcoding
        )
        return coordinator.run()
