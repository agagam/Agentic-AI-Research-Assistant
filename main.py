import os
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from agents import websearch_agent, reader_agent, email_agent
import prompts

# Environment variable check
REQUIRED_VARS = ["DB_HOST", "DB_PASSWORD", "SERPAPI_KEY", "EMAIL_USER", "EMAIL_PASS", "RECIPIENT_EMAIL"]
for var in REQUIRED_VARS:
    if not os.getenv(var):
        raise ValueError(f"Missing environment variable: {var}")

# Combine sub-agents into the Coordinator
academic_coordinator = LlmAgent(
    name="academic_coordinator",
    model="gemini-3.6-flash",
    description="Orchestrates research discovery, database logging, and email reporting.",
    instruction=prompts.ACADEMIC_COORDINATOR_PROMPT,
    tools=[
        AgentTool(agent=websearch_agent),
        AgentTool(agent=reader_agent),
        AgentTool(agent=email_agent),
    ],
)

if __name__ == "__main__":
    # Start the autonomous process
    response = academic_coordinator.run("Find new Arabidopsis research from this week and email the summary.")
    print(f"Workflow Status: {response.text}")
