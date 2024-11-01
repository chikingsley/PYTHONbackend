from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from utils.logging_config import setup_logging
from utils.error_handling import retry_with_backoff, handle_api_error
from utils.rate_limiter import APIRateLimiter
import requests

load_dotenv()

# Global variables
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
DOCUMENTS_DIR = "generated_documents"

# Initialize logger and rate limiter
logger = setup_logging("DocumentGenerator")
rate_limiter = APIRateLimiter()

# Ensure documents directory exists
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

class DocumentGenerator(BaseTool):
    """
    Generates construction documents using templates and project specifications.
    Uses Mistral AI for content generation and local storage for documents.
    """
    
    project_spec: dict = Field(
        ..., 
        description="Project specifications including type, scope, location, and requirements"
    )
    
    document_type: str = Field(
        ..., 
        description="Type of document to generate (e.g., 'contract', 'specification', 'plan')"
    )

    def _get_template(self, doc_type: str) -> str:
        """Get basic template based on document type"""
        templates = {
            "contract": """
# CONSTRUCTION CONTRACT

## Project Details
[Project Name]
[Location]
[Start Date]
[Completion Date]

## Scope of Work
[Detailed description of construction work]

## Terms and Conditions
1. Timeline
2. Payment Schedule
3. Materials
4. Labor
5. Warranties
6. Insurance Requirements

## Signatures
[Client Name]
[Contractor Name]
[Date]
            """,
            "specification": """
# TECHNICAL SPECIFICATIONS

## Project Overview
[Project Description]

## Materials Specifications
1. Structural Materials
2. Finishing Materials
3. Electrical Systems
4. Plumbing Systems

## Construction Requirements
1. Building Codes
2. Quality Standards
3. Testing Requirements

## Safety Requirements
[Safety protocols and requirements]
            """,
            "plan": """
# CONSTRUCTION PLAN

## Project Timeline
[Detailed timeline with milestones]

## Resource Allocation
1. Labor Requirements
2. Equipment Needs
3. Material Delivery Schedule

## Construction Phases
1. Site Preparation
2. Foundation Work
3. Structural Work
4. Finishing Work

## Quality Control Measures
[Quality control procedures and checkpoints]
            """
        }
        return templates.get(doc_type, "# CUSTOM DOCUMENT\n[Document Content]")

    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    @handle_api_error
    def run(self):
        """
        Generates a construction document based on project specifications and templates.
        """
        try:
            logger.info(f"Starting document generation for {self.document_type}")
            
            # Get base template
            template = self._get_template(self.document_type)
            
            # Wait for rate limit
            rate_limiter.acquire('mistral')
            
            # Generate document using Mistral
            logger.info("Generating document content using Mistral")
            headers = {
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            Generate a construction {self.document_type} document using the following:
            
            Template:
            {template}
            
            Project Specifications:
            {json.dumps(self.project_spec, indent=2)}
            
            Please fill in all placeholders with appropriate content based on the project specifications.
            Ensure the document follows industry standards and includes all required sections.
            The response should be in Markdown format.
            """
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "mistral-large-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 4000
                }
            )
            
            response.raise_for_status()
            document_content = response.json()["choices"][0]["message"]["content"]
            
            # Save document
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.document_type}_{timestamp}.md"
            filepath = os.path.join(DOCUMENTS_DIR, filename)
            
            with open(filepath, 'w') as f:
                f.write(document_content)
            
            # Save metadata
            metadata_file = os.path.join(DOCUMENTS_DIR, f"{filename}.meta.json")
            metadata = {
                "type": self.document_type,
                "timestamp": timestamp,
                "project_spec": self.project_spec
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Successfully generated {self.document_type} document: {filepath}")
            return {
                "status": "success",
                "message": f"Generated {self.document_type} document",
                "filepath": filepath
            }
            
        except Exception as e:
            logger.error(f"Error generating document: {str(e)}")
            raise

if __name__ == "__main__":
    # Test the tool
    test_spec = {
        "type": "residential",
        "scope": "New construction",
        "location": "New York",
        "requirements": {
            "size": "2000 sq ft",
            "stories": 2,
            "bedrooms": 3,
            "bathrooms": 2.5
        }
    }
    
    tool = DocumentGenerator(
        project_spec=test_spec,
        document_type="contract"
    )
    print(tool.run())
