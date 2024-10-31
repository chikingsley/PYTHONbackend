from agency_swarm import Agent
from .tools.cost_estimator import CostEstimator

class CostAnalysisAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Cost Analysis Agent",
            description="Specialized agent responsible for project cost estimation, analysis, and optimization",
            instructions="./instructions.md",
            tools=[CostEstimator],
            temperature=0.2,
            max_prompt_tokens=4000,
        ) 