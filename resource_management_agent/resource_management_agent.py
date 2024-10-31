from agency_swarm import Agent
from .tools.resource_allocator import ResourceAllocator
from .tools.resource_monitor import ResourceMonitor

class ResourceManagementAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Resource Management Agent",
            description="Specialized agent responsible for allocating and monitoring project resources",
            instructions="./instructions.md",
            tools=[ResourceAllocator, ResourceMonitor],
            temperature=0.2,
            max_prompt_tokens=4000,
        ) 