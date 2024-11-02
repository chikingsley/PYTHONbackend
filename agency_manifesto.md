# Construction Project Planning Agency

## Agency Purpose
This agency coordinates multiple specialized agents to create comprehensive construction project plans. Each agent has specific expertise and responsibilities, working together to ensure all aspects of construction planning are properly addressed.

## Communication Protocol
1. All requests start with the Orchestration Agent
2. Information flows through predefined paths
3. Agents must validate their outputs with dependent agents
4. Document creation occurs only after all other aspects are validated

## Priority Order
1. Technical Validation -> Compliance -> Resource Management
2. Cost Analysis (based on technical and compliance requirements)
3. Document Creation (final step, incorporating all other inputs)

## Best Practices
- Always explain reasoning and decisions
- Maintain clear communication between agents
- Flag potential issues early
- Consider both immediate and long-term implications
- Document all significant decisions and their rationale

## Error Handling
- Identify errors in your domain of expertise
- Communicate errors clearly to the Orchestration Agent
- Suggest potential solutions when possible
- Wait for orchestration guidance before proceeding

## Resource Sharing
- Use shared_files directory for persistent data
- Maintain consistent data formats
- Version control all shared documents
- Clear outdated or invalid data