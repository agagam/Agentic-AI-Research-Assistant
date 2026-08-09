import requests
import os
import psycopg2
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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




# --- Research Database Tool ---

def check_if_article_saved(title: str):
    """
    Checks the database to see if we have already saved this article title.
    Returns True if found, False otherwise.
    """
    # Connect to your Cloud SQL database
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
    
    # Run the query
    cur.execute("SELECT 1 FROM websearch_articles WHERE title = %s", (title,))
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return result is not None  # Returns True if a row was found




# --- Save New Article Tool ---

def clean_url(url: str) -> str:
    """
    Clean the links from agent's mistakes.
    """
    url = url.strip().strip("'\"")
    if url.startswith("httpshttps://"):
        url = url.replace("httpshttps://", "https://")
    if url.startswith("https'://"):
        url = url.replace("https'://", "https://")
    if url.startswith("httphttp://"):
        url = url.replace("httphttp://", "http://")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def save_new_article(title: str, link: str):
    """
    Saves a new article title and link to the research database.
    """
    cleaned_link = clean_url(link)
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
        cur.execute("INSERT INTO websearch_articles (title, link) VALUES (%s, %s)", (title, cleaned_link))
        conn.commit()
        return f"Successfully saved: {title}"
    except Exception as e:
        return f"Error saving article: {str(e)}"
    finally:
        cur.close()
        conn.close()



# --- Reading Research Article ---

def read_article_content(url: str):
    """Reads the text content of a website link."""
    cleaned_url = clean_url(url) 
    response = requests.get(cleaned_url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()[:5000] 



# --- Email Tool ---
def send_formatted_email(recipient_email, subject: str, html_body: str):
    """Sends a formatted HTML email."""
    msg = MIMEMultipart()
    msg['From'] = os.getenv("EMAIL_USER")
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(html_body, 'html'))
    
    # Simple SMTP setup
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        server.send_message(msg)
    return "Email sent successfully!"

