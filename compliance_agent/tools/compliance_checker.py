from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import duckdb
import anthropic
from tavily import TavilyClient
from pymilvus import connections, Collection

load_dotenv()

# Global variables
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DUCKDB_PATH = "compliance_store.db"
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

class ComplianceChecker(BaseTool):
    """
    Validates project compliance with local regulations, building codes, 
    and safety standards.
    """
    
    project_details: dict = Field(
        ..., 
        description="Project details including location, type, scope, and specifications"
    )
    
    check_type: str = Field(
        ..., 
        description="Type of compliance check (e.g., 'building_code', 'safety', 'permits')"
    )

    def run(self):
        """
        Performs compliance validation against relevant regulations and standards.
        """
        try:
            # Initialize connections
            db = duckdb.connect(DUCKDB_PATH)
            claude = anthropic.Client(api_key=CLAUDE_API_KEY)
            tavily = TavilyClient(api_key=TAVILY_API_KEY)
            connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
            
            # Research local regulations
            location = self.project_details.get('location', '')
            search_results = tavily.search(
                query=f"construction {self.check_type} regulations {location}",
                search_depth="advanced"
            )
            
            # Find similar compliance cases
            compliance_collection = Collection("compliance_cases")
            compliance_collection.load()
            
            results = compliance_collection.search(
                data=[self.project_details["embedding"]],
                anns_field="embedding",
                param={"metric_type": "L2", "params": {"nprobe": 10}},
                limit=3
            )
            
            similar_cases = [result.entity.get('case_details') for result in results[0]]
            
            # Validate using Claude
            prompt = f"""
            Validate project compliance for the following:
            
            Project Details:
            {self.project_details}
            
            Compliance Type: {self.check_type}
            
            Local Regulations:
            {search_results}
            
            Similar Cases:
            {similar_cases}
            
            Please provide:
            1. Compliance status
            2. Required permits
            3. Potential violations
            4. Recommended actions
            5. Risk assessment
            """
            
            message = claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            compliance_results = message.content
            
            # Store results
            db.execute("""
                INSERT INTO compliance_checks (project_location, check_type, results)
                VALUES (?, ?, ?)
            """, (location, self.check_type, compliance_results))
            
            return compliance_results
            
        except Exception as e:
            return f"Error checking compliance: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    test_project = {
        "location": "New York City",
        "type": "commercial",
        "scope": "New construction",
        "specifications": {
            "height": "120 feet",
            "area": "50000 sqft"
        },
        "embedding": [0.1] * 1536  # Example embedding
    }
    
    tool = ComplianceChecker(
        project_details=test_project,
        check_type="building_code"
    )
    print(tool.run()) 