from google.adk import Agent
from google.adk.tools import google_search
from . import prompts
from . import tools
import os

recipient = os.getenv("RECIPIENT_EMAIL")
MODEL = "gemini-1.5-flash"

websearch_agent = Agent(
    model = MODEL,
    name = "websearch-agent",
    instruction = prompts.WEBSEARCH_PROMPT,
    tools = tools.my_research_tools
)

reader_agent = Agent(
    model = MODEL,
    name = "reader-agent",
    instruction = prompts.READER_PROMPT,
    tools = tools.summary_tools
)


formatted_instruction = prompts.EMAIL_PROMPT.format(my_email_address=recipient)
email_agent = Agent(
    model = MODEL,
    name = "email-agent",
    instruction = formatted_instruction,
    tools = tools.email_tools
)
