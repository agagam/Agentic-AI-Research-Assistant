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
    """Fetch and read the text content of a research article from a given URL link."""
    cleaned_url = clean_url(url)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,pl;q=0.8",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(cleaned_url, headers=headers, timeout=10)
        
        # paywall
        if response.status_code != 200:
            return f"Status {response.status_code}: Access restricted by publisher."
            
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text().strip()
        
        if len(text) < 200:
            return "Content blocked by JavaScript challenge or Cloudflare."
            
        return text[:5000] 
        
    except Exception as e:
        return f"Error fetching page: {str(e)}"




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

