import requests
import os
import psycopg2
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from vertexai.generative_models import FunctionDeclaration, Tool


# --- Google Scholar Search Tool ---

def search_google_scholar(query: str):
    """
    Search Google Scholar for academic papers and citations.
    """
    url = "https://serpapi.com/search"
    api_key = os.getenv("SERPAPI_KEY")

    params = {
        "engine": "google_scholar",
        "q": query,
        "as_ylo": "2026",  
        "api_key": api_key 
    }
    
    response = requests.get(url, params=params)
    results = response.json()
    
    # Tile and link from the Google Scholar results
    summaries = []
    for paper in results.get("organic_results", []):
        summaries.append(f"Title: {paper['title']}, Link: {paper['link']}")
    
    return "\n".join(summaries)


search_tool_declaration = FunctionDeclaration(
    name="search_google_scholar",
    description="Search Google Scholar for academic publications and research papers.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The research topic or keywords"}
        },
    },
)



# --- Research Database Tool ---

def check_if_article_saved(title: str):
    """
    Checks the database to see if we have already saved this article link.
    Returns True if found, False otherwise.
    """
    # Connect to your Cloud SQL database
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),      # The IP address of your Cloud SQL instance
        database="postgres",
        user="postgres",
        password=os.getenv("DB_PASSWORD"),

        # SSL Configuration
        sslmode="verify-ca",                   
        sslrootcert=os.getenv("DB_SSL_CA"),    
        sslcert=os.getenv("DB_SSL_CERT"),      
        sslkey=os.getenv("DB_SSL_KEY")   
    )
    
    cur = conn.cursor()
    
    # Run the query
    cur.execute("SELECT 1 FROM websearch_articles WHERE title = %s", (title))
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return result is not None  # Returns True if a row was found


check_tool_declaration = FunctionDeclaration(
    name="check_if_article_saved",
    description="Check if an article title is already in our database.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The title of the article"}
        },
        "required": ["title"]
    },
)


# --- Save New Article Tool ---

def save_new_article(title: str, link: str):
    """
    Saves a new article title and link to the research database.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database="postgres",
        user="postgres",
        password=os.getenv("DB_PASSWORD"),

        # SSL Configuration
        sslmode="verify-ca",                   
        sslrootcert=os.getenv("DB_SSL_CA"),    
        sslcert=os.getenv("DB_SSL_CERT"),      
        sslkey=os.getenv("DB_SSL_KEY")   
    )
    cur = conn.cursor()
    
    try:
        cur.execute("INSERT INTO websearch_articles (title, link) VALUES (%s, %s)", (title, link))
        conn.commit()
        return f"Successfully saved: {title}"
    except Exception as e:
        return f"Error saving article: {str(e)}"
    finally:
        cur.close()
        conn.close()

save_tool_declaration = FunctionDeclaration(
    name="save_new_article",
    description="Save a new article title and link to the database.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "link": {"type": "string"}
        },
        "required": ["title", "link"]
    },
)

my_research_tools = Tool(function_declarations=[
    check_tool_declaration,
    search_tool_declaration,
    save_tool_declaration  
])



# --- Reading Research Article ---

def read_article_content(url: str):
    """Reads the text content of a website link."""
    response = requests.get(url, timeout=10)
    # Basic cleanup to remove HTML tags and get text
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()[:5000] # Limit to 5000 chars to save context space

read_article_tool_declaration = FunctionDeclaration(
    name="read_article_content",
    description="Fetch and read the text content of a research article from a given URL link.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string", 
                "description": "The full URL of the academic article or webpage to be read."
            }
        },
        "required": ["url"]
    },
)

summary_tools = Tool(function_declarations=[read_article_tool_declaration])


# --- Email Tool ---
def send_formatted_email(recipient_email, subject: str, html_body: str):
    """Sends a formatted HTML email."""
    msg = MIMEMultipart()
    msg['From'] = "research-bot@gmail.com"
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(html_body, 'html'))
    
    # Simple SMTP setup (example for Gmail)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        server.send_message(msg)
    return "Email sent successfully!"

email_tool_declaration = FunctionDeclaration(
    name="send_formatted_email",
    description="Send a professionally formatted HTML email to a recipient.",
    parameters={
        "type": "object",
        "properties": {
            "recipient_email": {
                "type": "string",
                "description": "The email address of the person receiving the research update."
            },
            "subject": {
                "type": "string",
                "description": "The subject line for the email (e.g., 'New Arabidopsis Research Update')."
            },
            "html_body": {
                "type": "string",
                "description": "The full HTML code for the email body, including styles, headers, and summaries."
            }
        },
        "required": ["recipient_email", "subject", "html_body"]
    },
)

email_tools = Tool(function_declarations=[email_tool_declaration])
