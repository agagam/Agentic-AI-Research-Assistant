from google.adk.agents import LlmAgent
from . import prompts
from . import tools
import os

recipient = os.getenv("RECIPIENT_EMAIL")
MODEL1 = "gemini-2.5-pro"
MODEL2 = "gemini-2.5-flash"

websearch_agent = LlmAgent(
    model = MODEL1,
    name = "websearch_agent",
    description = "Searches Google Scholar for scientific articles and checks if they are saved in the database.",
    instruction = prompts.WEBSEARCH_PROMPT,
    output_key = "",
    tools = [
        tools.search_google_scholar, 
        tools.check_if_article_saved, 
        tools.save_new_article
    ]
)

reader_agent = LlmAgent(
    model = MODEL2,
    name = "reader_agent",
    description = "Fetches and reads the full text of a scientific article from a URL and provides a structured summary.",
    instruction = prompts.READER_PROMPT,
    output_key = "",
    tools = [tools.read_article_content]
)

formatted_instruction = prompts.EMAIL_PROMPT.format(my_email_address=recipient)
email_agent = LlmAgent(
    model = MODEL2,
    name = "email_agent",
    description = "Formats summaries of scientific research into beautiful HTML and sends email updates.",
    instruction = formatted_instruction,
    output_key = "",
    tools = [tools.send_formatted_email]
)
