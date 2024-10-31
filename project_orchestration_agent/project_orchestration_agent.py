from agency_swarm import Agent
from .tools.workflow_coordinator import WorkflowCoordinator

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