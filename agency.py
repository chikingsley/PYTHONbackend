from agency_swarm import Agency
from document_creation_agent.document_creation_agent import DocumentCreationAgent
from technical_validation_agent.technical_validation_agent import TechnicalValidationAgent
from compliance_agent.compliance_agent import ComplianceAgent
from cost_analysis_agent.cost_analysis_agent import CostAnalysisAgent
from project_orchestration_agent.project_orchestration_agent import ProjectOrchestrationAgent
from resource_management_agent.resource_management_agent import ResourceManagementAgent

# Initialize agents
doc_agent = DocumentCreationAgent()
tech_agent = TechnicalValidationAgent()
compliance_agent = ComplianceAgent()
cost_agent = CostAnalysisAgent()
orchestration_agent = ProjectOrchestrationAgent()
resource_agent = ResourceManagementAgent()

# Create the agency with communication flows
construction_agency = Agency(
    [
        orchestration_agent,  # Entry point for user communication
        [orchestration_agent, doc_agent],  # Orchestrator can communicate with Document Creation
        [orchestration_agent, tech_agent],  # Orchestrator can communicate with Technical Validation
        [orchestration_agent, compliance_agent],  # Orchestrator can communicate with Compliance
        [orchestration_agent, cost_agent],  # Orchestrator can communicate with Cost Analysis
        [orchestration_agent, resource_agent],  # Orchestrator can communicate with Resource Management
        [doc_agent, tech_agent],  # Document Creation can communicate with Technical Validation
        [doc_agent, compliance_agent],  # Document Creation can communicate with Compliance
        [doc_agent, cost_agent],  # Document Creation can communicate with Cost Analysis
        [tech_agent, compliance_agent],  # Technical Validation can communicate with Compliance
        [tech_agent, resource_agent],  # Technical Validation can communicate with Resource Management
        [compliance_agent, resource_agent],  # Compliance can communicate with Resource Management
        [cost_agent, resource_agent],  # Cost Analysis can communicate with Resource Management
    ],
    shared_instructions="agency_manifesto.md",  # Shared instructions for all agents
    temperature=0.2,  # Default temperature for all agents
    max_prompt_tokens=4000  # Default max tokens in conversation history
)

if __name__ == "__main__":
    # Start the agency in demo mode
    construction_agency.run_demo() 