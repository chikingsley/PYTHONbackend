from agency_swarm import Agent
from agency_swarm.tools import BaseTool, CodeInterpreter
from pydantic import Field
from typing import Dict, List, Any
import duckdb
import httpx
import os

class TechnicalStandard(BaseTool):
    standard_id: str
    category: str
    requirements: List[str]
    metadata: Dict[str, Any]

class ResearchStandards(BaseTool):
    """Research current technical standards using Tavily"""
    construction_type: str = Field(..., description="Type of construction")
    location: str = Field(..., description="Project location")

    def run(self):
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        client = httpx.Client(headers={"Authorization": f"Bearer {tavily_api_key}"})
        
        response = client.get(
            "https://api.tavily.com/search",
            params={
                "query": f"construction standards {self.construction_type} {self.location}",
                "search_depth": "advanced",
                "include_domains": ["building-codes.com", "constructionstandards.org"]
            }
        )
        
        standards = response.json()
        # Store standards in DuckDB
        self.db.execute("""
            INSERT INTO technical_standards (standard_id, category, requirements, metadata)
            VALUES (?, ?, ?, ?)
        """, (standards["id"], self.construction_type, standards["requirements"], standards["metadata"]))
        
        return standards

class ValidateSpecifications(BaseTool):
    """Validate technical specifications against standards"""
    specs: Dict[str, Any] = Field(..., description="Technical specifications to validate")
    standard_ids: List[str] = Field(..., description="IDs of standards to validate against")

    def run(self):
        # Get standards from DuckDB
        standards = self.db.execute("""
            SELECT * FROM technical_standards 
            WHERE standard_id IN (?)
        """, (self.standard_ids,)).fetchall()
        
        validation_results = []
        for standard in standards:
            result = self.validate_against_standard(self.specs, standard)
            validation_results.append(result)
            
            # Log validation in history
            self.db.execute("""
                INSERT INTO validation_history 
                (spec_id, standard_id, result, timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (self.specs["id"], standard["standard_id"], result))
        
        return validation_results

class TechnicalValidationAgent(Agent):
    def __init__(self, **kwargs):
        # Initialize DuckDB
        self.db = duckdb.connect('technical_validation.db')
        self.setup_database()
        
        # Add tools
        tools = kwargs.get('tools', []) + [
            ResearchStandards,
            ValidateSpecifications,
            CodeInterpreter
        ]
        
        super().__init__(
            name="Technical Validation Agent",
            description="I validate technical specifications and ensure construction plan feasibility.",
            instructions="./technical_validation_agent/instructions.md",
            tools=tools,
            **kwargs
        )

    def setup_database(self):
        """Initialize DuckDB tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS technical_standards (
                standard_id VARCHAR PRIMARY KEY,
                category VARCHAR,
                requirements JSON,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS validation_history (
                validation_id INTEGER PRIMARY KEY,
                spec_id VARCHAR,
                standard_id VARCHAR,
                result JSON,
                timestamp TIMESTAMP
            );
        """)