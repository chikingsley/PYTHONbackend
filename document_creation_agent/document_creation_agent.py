from agency_swarm import Agent
from .tools.document_generator import DocumentGenerator

class DocumentCreationAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Document Creation Agent",
            description="Specialized agent responsible for creating, managing and validating construction documentation",
            instructions="./instructions.md",
            tools=[DocumentGenerator],
            temperature=0.2,
            max_prompt_tokens=4000,
        ) 