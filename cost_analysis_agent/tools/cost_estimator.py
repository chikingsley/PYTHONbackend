from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import duckdb
import anthropic
from tavily import TavilyClient

load_dotenv()

# Global variables
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DUCKDB_PATH = "cost_store.db"

class CostEstimator(BaseTool):
    """
    Analyzes and estimates project costs based on specifications, market rates,
    and historical data.
    """
    
    project_specs: dict = Field(
        ..., 
        description="Project specifications including materials, labor, timeline, and location"
    )
    
    estimate_type: str = Field(
        ..., 
        description="Type of estimate required (e.g., 'initial', 'detailed', 'change_order')"
    )

    def run(self):
        """
        Generates detailed cost estimates based on current market rates and project specifications.
        """
        try:
            # Initialize clients
            db = duckdb.connect(DUCKDB_PATH)
            claude = anthropic.Client(api_key=CLAUDE_API_KEY)
            tavily = TavilyClient(api_key=TAVILY_API_KEY)
            
            # Research current market rates
            location = self.project_specs.get('location', '')
            search_results = tavily.search(
                query=f"current construction costs {location} {self.project_specs.get('type', '')}",
                search_depth="advanced",
                include_domains=["rsmeans.com", "constructioncosts.info"]
            )
            
            # Extract market rates
            market_data = "\n".join([result['content'] for result in search_results])
            
            # Generate estimate using Claude
            prompt = f"""
            Generate a detailed cost estimate for the following construction project:
            
            Project Specifications:
            {self.project_specs}
            
            Estimate Type: {self.estimate_type}
            
            Current Market Rates:
            {market_data}
            
            Please provide:
            1. Detailed cost breakdown
            2. Labor costs
            3. Material costs
            4. Equipment costs
            5. Overhead and profit
            6. Contingency recommendations
            7. Cost risk analysis
            """
            
            message = claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            estimate_results = message.content
            
            # Store estimate
            db.execute("""
                INSERT INTO cost_estimates (location, estimate_type, specifications, results)
                VALUES (?, ?, ?, ?)
            """, (location, self.estimate_type, str(self.project_specs), estimate_results))
            
            return estimate_results
            
        except Exception as e:
            return f"Error generating cost estimate: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    test_specs = {
        "type": "commercial",
        "location": "New York City",
        "area": "50000 sqft",
        "materials": {
            "concrete": "5000 cubic yards",
            "steel": "500 tons"
        },
        "timeline": "18 months"
    }
    
    tool = CostEstimator(
        project_specs=test_specs,
        estimate_type="detailed"
    )
    print(tool.run()) 