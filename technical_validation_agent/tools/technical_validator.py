from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import duckdb
import anthropic
from tavily import TavilyClient
from utils.logging_config import setup_logging
from utils.error_handling import retry_with_backoff, handle_api_error
from utils.rate_limiter import APIRateLimiter

load_dotenv()

# Global variables
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DUCKDB_PATH = "technical_store.db"

# Initialize logger and rate limiter
logger = setup_logging("TechnicalValidator")
rate_limiter = APIRateLimiter()

class TechnicalValidator(BaseTool):
    """
    Validates technical specifications and construction methodologies against 
    industry standards and best practices.
    """
    
    specifications: dict = Field(
        ..., 
        description="Technical specifications to validate. Can include area, conversion_type, special_requirements, compliance_standards, systems, materials, methods, and timeline"
    )
    
    project_type: str = Field(
        ..., 
        description="Type of construction project (e.g., 'residential', 'commercial', 'industrial')"
    )

    def _format_specifications_for_prompt(self, specs):
        """Helper method to format specifications consistently"""
        formatted_specs = []
        
        # Handle area and conversion type if present
        if 'area' in specs:
            formatted_specs.append(f"Area: {specs['area']}")
        if 'conversion_type' in specs:
            formatted_specs.append(f"Conversion Type: {specs['conversion_type']}")
            
        # Handle special requirements
        if 'special_requirements' in specs:
            formatted_specs.append("Special Requirements:")
            for req in specs['special_requirements']:
                formatted_specs.append(f"- {req}")
                
        # Handle compliance standards
        if 'compliance_standards' in specs:
            formatted_specs.append("Compliance Standards:")
            for std in specs['compliance_standards']:
                formatted_specs.append(f"- {std}")
                
        # Handle systems
        if 'systems' in specs:
            formatted_specs.append("Systems:")
            for sys in specs['systems']:
                formatted_specs.append(f"- {sys}")
                
        # Handle traditional format (materials, methods, timeline)
        if 'materials' in specs:
            formatted_specs.append("Materials:")
            for mat, desc in specs['materials'].items():
                formatted_specs.append(f"- {mat}: {desc}")
                
        if 'methods' in specs:
            formatted_specs.append("Methods:")
            for method, desc in specs['methods'].items():
                formatted_specs.append(f"- {method}: {desc}")
                
        if 'timeline' in specs:
            formatted_specs.append("Timeline:")
            for phase, duration in specs['timeline'].items():
                formatted_specs.append(f"- {phase}: {duration}")
                
        return "\n".join(formatted_specs)

    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    @handle_api_error
    def run(self):
        """
        Validates technical specifications against current standards and best practices.
        """
        try:
            logger.info(f"Starting technical validation for {self.project_type} project")
            
            # Initialize clients
            db = duckdb.connect(DUCKDB_PATH)
            claude = anthropic.Client(api_key=CLAUDE_API_KEY)
            tavily = TavilyClient(api_key=TAVILY_API_KEY)
            
            # Format specifications consistently
            formatted_specs = self._format_specifications_for_prompt(self.specifications)
            
            # Research current standards
            logger.info("Researching current standards")
            rate_limiter.acquire('tavily')
            search_results = tavily.search(
                query=f"latest construction standards and specifications for {self.project_type} projects",
                search_depth="advanced",
                include_domains=["constructionstandards.org", "buildingcodes.com"]
            )
            
            # Extract relevant standards
            standards_summary = "\n".join([result['content'] for result in search_results])
            
            # Validate using Claude
            logger.info("Validating specifications using Claude")
            rate_limiter.acquire('claude')
            prompt = f"""
            Validate the following technical specifications against current industry standards:
            
            Specifications:
            {formatted_specs}
            
            Current Standards and Best Practices:
            {standards_summary}
            
            Please analyze and provide:
            1. Compliance with current standards
            2. Potential technical issues
            3. Timeline feasibility
            4. Safety considerations
            5. Recommended improvements
            """
            
            message = claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            validation_results = message.content
            
            # Store validation results
            logger.info("Storing validation results")
            db.execute("""
                INSERT INTO validations (project_type, specifications, results)
                VALUES (?, ?, ?)
            """, (self.project_type, str(self.specifications), validation_results))
            
            logger.info("Technical validation completed successfully")
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating specifications: {str(e)}")
            raise

if __name__ == "__main__":
    # Test the tool
    test_specs = {
        "materials": {
            "concrete": "Type II Portland Cement",
            "reinforcement": "Grade 60 rebar"
        },
        "methods": {
            "foundation": "Spread footing",
            "construction_type": "Cast-in-place"
        },
        "timeline": {
            "foundation": "4 weeks",
            "structure": "12 weeks"
        }
    }
    
    tool = TechnicalValidator(
        specifications=test_specs,
        project_type="commercial"
    )
    print(tool.run()) 