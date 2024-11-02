from agency_swarm import Agent
from agency_swarm.tools import BaseTool, CodeInterpreter
from pydantic import Field, BaseModel
from typing import Dict, List, Any
import duckdb
import httpx
import os

class CostEstimate(BaseModel):
    estimate_id: str
    category: str
    costs: Dict[str, float]
    metadata: Dict[str, Any]

class ResearchMarketRates(BaseTool):
    """Research current market rates using Tavily"""
    project_type: str = Field(..., description="Type of construction")
    location: str = Field(..., description="Project location")
    materials: List[str] = Field(..., description="Required materials")

    def run(self):
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        client = httpx.Client(headers={"Authorization": f"Bearer {tavily_api_key}"})
        
        # Research material costs
        material_costs = {}
        for material in self.materials:
            response = client.get(
                "https://api.tavily.com/search",
                params={
                    "query": f"{material} construction cost {self.location}",
                    "search_depth": "advanced",
                    "include_domains": ["construction-costs.com", "materialprices.org"]
                }
            )
            material_costs[material] = response.json()
        
        # Research labor rates
        labor_response = client.get(
            "https://api.tavily.com/search",
            params={
                "query": f"construction labor rates {self.project_type} {self.location}",
                "search_depth": "advanced"
            }
        )
        
        market_data = {
            "material_costs": material_costs,
            "labor_rates": labor_response.json()
        }
        
        # Store in DuckDB
        self.db.execute("""
            INSERT INTO market_rates (location, project_type, rates, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (self.location, self.project_type, market_data))
        
        return market_data

class GenerateEstimate(BaseTool):
    """Generate cost estimate for project"""
    project: Dict[str, Any] = Field(..., description="Project specifications")
    market_rates: Dict[str, Any] = Field(..., description="Current market rates")

    def run(self):
        estimate = self.calculate_estimate(self.project, self.market_rates)
        
        # Store estimate in DuckDB
        self.db.execute("""
            INSERT INTO cost_estimates 
            (project_id, estimate, created_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (self.project["id"], estimate))
        
        return estimate

    def calculate_estimate(self, project: Dict[str, Any], rates: Dict[str, Any]) -> Dict[str, Any]:
        # Implement detailed cost calculation logic here
        total_cost = 0
        cost_breakdown = {}
        
        # Calculate material costs
        for material, quantity in project.get("materials", {}).items():
            unit_cost = rates["material_costs"].get(material, {}).get("price", 0)
            cost_breakdown[material] = quantity * unit_cost
            total_cost += cost_breakdown[material]
        
        # Add labor costs
        labor_hours = project.get("estimated_labor_hours", 0)
        labor_rate = rates["labor_rates"].get("average_rate", 0)
        labor_cost = labor_hours * labor_rate
        cost_breakdown["labor"] = labor_cost
        total_cost += labor_cost
        
        # Add overhead and profit
        overhead_rate = 0.15  # 15% overhead
        profit_rate = 0.10    # 10% profit
        
        overhead = total_cost * overhead_rate
        profit = total_cost * profit_rate
        
        return {
            "total_cost": total_cost + overhead + profit,
            "breakdown": cost_breakdown,
            "overhead": overhead,
            "profit": profit
        }

class CostAnalysisAgent(Agent):
    def __init__(self, **kwargs):
        # Initialize DuckDB
        self.db = duckdb.connect('cost_analysis.db')
        self.setup_database()
        
        # Add tools
        tools = kwargs.get('tools', []) + [
            ResearchMarketRates,
            GenerateEstimate,
            CodeInterpreter
        ]
        
        super().__init__(
            name="Cost Analysis Agent",
            description="I analyze and optimize project costs while maintaining quality standards.",
            instructions="./cost_analysis_agent/instructions.md",
            tools=tools,
            **kwargs
        )

    def setup_database(self):
        """Initialize DuckDB tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS market_rates (
                rate_id INTEGER PRIMARY KEY,
                location VARCHAR,
                project_type VARCHAR,
                rates JSON,
                timestamp TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS cost_estimates (
                estimate_id INTEGER PRIMARY KEY,
                project_id VARCHAR,
                estimate JSON,
                created_at TIMESTAMP
            );
        """)