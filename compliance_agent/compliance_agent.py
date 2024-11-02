from agency_swarm import Agent
from agency_swarm.tools import BaseTool, CodeInterpreter
from pydantic import Field, BaseModel
from typing import Dict, List, Any
import duckdb
import httpx
from pymilvus import connections, Collection
import os

class Regulation(BaseModel):
    reg_id: str
    jurisdiction: str
    requirements: List[str]
    metadata: Dict[str, Any]

class ResearchRegulations(BaseTool):
    """Research local regulations and building codes using Tavily"""
    location: str = Field(..., description="Project location")
    project_type: str = Field(..., description="Type of construction project")

    def run(self):
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        client = httpx.Client(headers={"Authorization": f"Bearer {tavily_api_key}"})
        
        response = client.get(
            "https://api.tavily.com/search",
            params={
                "query": f"building codes regulations {self.project_type} {self.location}",
                "search_depth": "advanced",
                "include_domains": ["codes.gov", "buildingcodes.com"]
            }
        )
        
        regulations = response.json()
        
        # Store in DuckDB
        self.db.execute("""
            INSERT INTO regulations (reg_id, jurisdiction, requirements, metadata)
            VALUES (?, ?, ?, ?)
        """, (regulations["id"], self.location, regulations["requirements"], regulations["metadata"]))
        
        return regulations

class FindSimilarCases(BaseTool):
    """Find similar compliance cases using Milvus"""
    project_details: Dict[str, Any] = Field(..., description="Project specifications")
    limit: int = Field(default=5, description="Number of similar cases to find")

    def run(self):
        # Search Milvus for similar cases
        similar_cases = self.vector_db.search(
            collection="compliance_cases",
            vector=self.project_details.get("embedding"),
            limit=self.limit
        )
        
        return similar_cases

class ValidateCompliance(BaseTool):
    """Validate project compliance with regulations"""
    project: Dict[str, Any] = Field(..., description="Project details")
    regulations: List[str] = Field(..., description="Regulation IDs to check against")

    def run(self):
        # Get regulations from DuckDB
        regs = self.db.execute("""
            SELECT * FROM regulations 
            WHERE reg_id IN (?)
        """, (self.regulations,)).fetchall()
        
        validation_results = []
        for reg in regs:
            result = self.validate_against_regulation(self.project, reg)
            validation_results.append(result)
            
            # Log validation
            self.db.execute("""
                INSERT INTO compliance_checks 
                (project_id, reg_id, result, timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (self.project["id"], reg["reg_id"], result))
        
        return validation_results

class ComplianceAgent(Agent):
    def __init__(self, **kwargs):
        # Initialize DuckDB
        self.db = duckdb.connect('compliance.db')
        self.setup_database()
        
        # Initialize vector storage
        self.use_milvus = kwargs.get('use_milvus', False)
        if self.use_milvus:
            connections.connect(host='localhost', port='19530')
            self.vector_db = Collection("compliance_cases")
        
        # Add tools
        tools = kwargs.get('tools', []) + [
            ResearchRegulations,
            FindSimilarCases,
            ValidateCompliance,
            CodeInterpreter
        ]
        
        super().__init__(
            name="Compliance Agent",
            description="I ensure regulatory compliance and manage permit requirements.",
            instructions="./compliance_agent/instructions.md",
            tools=tools,
            **kwargs
        )

    def search_similar_cases(self, embedding, limit=5):
        """Search for similar cases using either Milvus or DuckDB"""
        if self.use_milvus:
            return self.vector_db.search(
                collection="compliance_cases",
                vector=embedding,
                limit=limit
            )
        else:
            # Use cosine similarity in DuckDB
            return self.db.execute("""
                WITH vector_similarities AS (
                    SELECT 
                        id,
                        1 - (
                            DOT_PRODUCT(vector, ?)
                            / (SQRT(DOT_PRODUCT(vector, vector)) * SQRT(DOT_PRODUCT(?, ?)))
                        ) as distance
                    FROM vector_store
                    WHERE collection = 'compliance_cases'
                    ORDER BY distance ASC
                    LIMIT ?
                )
                SELECT c.*, v.distance
                FROM vector_similarities v
                JOIN compliance_cases c ON c.case_id = v.id
            """, (embedding, embedding, embedding, limit)).fetchall()

    def setup_database(self):
        """Initialize DuckDB tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS regulations (
                reg_id VARCHAR PRIMARY KEY,
                jurisdiction VARCHAR,
                requirements JSON,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS compliance_checks (
                check_id INTEGER PRIMARY KEY,
                project_id VARCHAR,
                reg_id VARCHAR,
                result JSON,
                timestamp TIMESTAMP
            );
        """)