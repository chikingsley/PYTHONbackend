from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import duckdb
from pymilvus import connections, Collection
import anthropic
from utils.logging_config import setup_logging
from utils.error_handling import retry_with_backoff, handle_api_error
from utils.rate_limiter import APIRateLimiter

load_dotenv()

# Global variables
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
DUCKDB_PATH = "document_store.db"
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

# Initialize logger and rate limiter
logger = setup_logging("DocumentGenerator")
rate_limiter = APIRateLimiter()

class DocumentGenerator(BaseTool):
    """
    Generates construction documents using templates and project specifications.
    Uses Claude AI for content generation and Milvus for template matching.
    """
    
    project_spec: dict = Field(
        ..., 
        description="Project specifications including type, scope, location, and requirements"
    )
    
    document_type: str = Field(
        ..., 
        description="Type of document to generate (e.g., 'contract', 'specification', 'plan')"
    )

    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    @handle_api_error
    def run(self):
        """
        Generates a construction document based on project specifications and templates.
        """
        try:
            logger.info(f"Starting document generation for {self.document_type}")
            
            # Initialize connections
            db = duckdb.connect(DUCKDB_PATH)
            connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
            claude = anthropic.Client(api_key=CLAUDE_API_KEY)
            
            # Find similar templates
            template_collection = Collection("document_templates")
            template_collection.load()
            
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10},
            }
            
            logger.info("Searching for similar templates")
            results = template_collection.search(
                data=[self.project_spec["embedding"]],
                anns_field="embedding",
                param=search_params,
                limit=1
            )
            
            template = results[0][0].entity.get('template')
            
            # Wait for rate limit
            rate_limiter.acquire('claude')
            
            # Generate document using Claude
            logger.info("Generating document content using Claude")
            prompt = f"""
            Generate a construction {self.document_type} document using the following:
            
            Template:
            {template}
            
            Project Specifications:
            {self.project_spec}
            
            Ensure the document follows industry standards and includes all required sections.
            """
            
            message = claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            document_content = message.content
            
            # Store document metadata
            logger.info("Storing document metadata")
            db.execute("""
                INSERT INTO documents (type, content, metadata)
                VALUES (?, ?, ?)
            """, (self.document_type, document_content, self.project_spec))
            
            logger.info(f"Successfully generated {self.document_type} document")
            return f"Successfully generated {self.document_type} document"
            
        except Exception as e:
            logger.error(f"Error generating document: {str(e)}")
            raise

if __name__ == "__main__":
    # Test the tool
    test_spec = {
        "type": "residential",
        "scope": "New construction",
        "location": "New York",
        "embedding": [0.1] * 1536  # Example embedding
    }
    
    tool = DocumentGenerator(
        project_spec=test_spec,
        document_type="contract"
    )
    print(tool.run()) 