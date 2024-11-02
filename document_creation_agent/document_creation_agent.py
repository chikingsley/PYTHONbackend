from agency_swarm import Agent
from agency_swarm.tools import BaseTool, CodeInterpreter, FileSearch
from pydantic import Field, BaseModel
from typing import Dict, List, Any, Optional
import duckdb
from pymilvus import connections, Collection

class DocumentTemplate(BaseModel):
    template_id: str
    content: str
    metadata: Dict[str, Any]

class CreateDocument(BaseTool):
    """Create a new project document using templates"""
    spec: Dict[str, Any] = Field(..., description="Document specifications")
    template_type: str = Field(..., description="Type of template to use")

    def run(self):
        # Get similar templates from Milvus
        similar_templates = self.vector_db.search(
            collection="templates",
            vector=self.spec.get("embedding"),
            limit=1
        )
        
        # Generate document using template
        doc = self.create_from_template(similar_templates[0], self.spec)
        
        # Store metadata in DuckDB
        self.db.execute("""
            INSERT INTO document_metadata (doc_id, template_id, metadata)
            VALUES (?, ?, ?)
        """, (doc.id, similar_templates[0].id, doc.metadata))
        
        return doc

class UpdateDocument(BaseTool):
    """Update an existing document"""
    doc_id: str = Field(..., description="Document identifier")
    changes: Dict[str, Any] = Field(..., description="Changes to apply")
    reason: str = Field(..., description="Reason for update")

    def run(self):
        # Update document and track version
        self.db.execute("""
            INSERT INTO document_versions (doc_id, version, changes, reason)
            VALUES (?, ?, ?, ?)
        """, (self.doc_id, self.get_next_version(), self.changes, self.reason))
        return f"Document {self.doc_id} updated"

class ValidateDocument(BaseTool):
    """Validate document completeness and accuracy"""
    doc_id: str = Field(..., description="Document to validate")
    requirements: List[str] = Field(..., description="Validation requirements")

    def run(self):
        # Validate document against requirements
        validation_results = self.validate_against_requirements(
            self.doc_id, 
            self.requirements
        )
        return validation_results

class DocumentCreationAgent(Agent):
    def __init__(self, **kwargs):
        # Initialize database connections
        self.db = duckdb.connect('document_store.db')
        self.setup_database()
        
        # Initialize Milvus connection
        connections.connect(host='localhost', port='19530')
        self.vector_db = Collection("templates")
        
        # Add tools
        tools = kwargs.get('tools', []) + [
            CreateDocument, 
            UpdateDocument, 
            ValidateDocument,
            CodeInterpreter,
            FileSearch
        ]
        
        super().__init__(
            name="Document Creation Agent",
            description="I create and manage comprehensive construction project documentation.",
            instructions="./document_creation_agent/instructions.md",
            tools=tools,
            **kwargs
        )

    def setup_database(self):
        """Initialize DuckDB tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS document_metadata (
                doc_id VARCHAR PRIMARY KEY,
                template_id VARCHAR,
                metadata JSON
            );
            CREATE TABLE IF NOT EXISTS document_versions (
                doc_id VARCHAR,
                version INT,
                changes JSON,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS templates (
                template_id VARCHAR PRIMARY KEY,
                content TEXT,
                metadata JSON
            );
        """)