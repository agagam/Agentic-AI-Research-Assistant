import os
import asyncio
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from subagents.agents import websearch_agent, reader_agent, email_agent
from google.adk.runners import Runner  
from google.adk.sessions import InMemorySessionService  
from google.genai import types  
import subagents.prompts as prompts
import prompt


REQUIRED_VARS = ["DB_HOST", "DB_PASSWORD", "SERPAPI_KEY", "EMAIL_USER", "EMAIL_PASS", "RECIPIENT_EMAIL"]
for var in REQUIRED_VARS:
    if not os.getenv(var):
        raise ValueError(f"Missing environment variable: {var}")

academic_coordinator = LlmAgent(
    name="academic_coordinator",
    model="gemini-2.5-pro",
    description="Orchestrates research discovery, database logging, and email reporting.",
    instruction=prompt.ACADEMIC_COORDINATOR_PROMPT,
    tools=[
        AgentTool(agent=websearch_agent),
        AgentTool(agent=reader_agent),
        AgentTool(agent=email_agent),
    ],
)

async def main():
    session_service = InMemorySessionService()
    runner = Runner(agent=academic_coordinator, app_name="academic_research_app", session_service=session_service)

    await session_service.create_session(app_name="academic_research_app", user_id="user_1", session_id="session_1")

    query = "Find new Arabidopsis research from this week and email the summary."
    content = types.Content(role='user', parts=[types.Part(text=query)])

    print("Running the agent...")
    

    async for event in runner.run_async(user_id="user_1", session_id="session_1", new_message=content):
        if hasattr(event, 'content') and event.content:
            print(".", end="", flush=True) 
        
        if event.is_final_response() and event.content:
            final_answer = event.content.parts[0].text
            print(f"\n\n[SUCCESS] Final answer of the agent:\n{final_answer}")

if __name__ == "__main__":
    asyncio.run(main())
