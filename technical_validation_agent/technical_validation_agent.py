from agency_swarm import Agent
from .tools.technical_validator import TechnicalValidator

class TechnicalValidationAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Technical Validation Agent",
            description="Specialized agent responsible for validating technical specifications and construction methodologies",
            instructions="./instructions.md",
            tools=[TechnicalValidator],
            temperature=0.2,
            max_prompt_tokens=4000,
        ) 