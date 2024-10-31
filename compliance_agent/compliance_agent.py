from agency_swarm import Agent
from .tools.compliance_checker import ComplianceChecker

class ComplianceAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Compliance Agent",
            description="Specialized agent responsible for ensuring regulatory compliance and permit management",
            instructions="./instructions.md",
            tools=[ComplianceChecker],
            temperature=0.2,
            max_prompt_tokens=4000,
        ) 