import requests
import os
import numpy as np
import psycopg2
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from . import relevance_gate as rg


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
        "as_ylo": "2023",  
        "api_key": api_key 
    }
    
    response = requests.get(url, params=params)
    results = response.json()
    
    summaries = []
    for paper in results.get("organic_results", []):
        snippet = paper.get("snippet", "")
        title = paper.get("title", "No Title Provided")
        
        link = paper.get("link")
        if not link or "example" in link or "no-link-provided" in link:
            resources = paper.get("resources", [])
            if resources and isinstance(resources, list):
                link = resources[0].get("link")
        
        if not link or "example.com" in link or "no-link-provided" in link:
            import urllib.parse
            encoded_title = urllib.parse.quote(title)
            link = f"https://scholar.google.com/scholar?q={encoded_title}"
            
        summaries.append(f"Title: {title}, Link: {link}, Snippet: {snippet}")
    
    return "\n".join(summaries)




# --- Research Database Tool ---

def _get_conn():
    key_path = os.getenv("DB_SSL_KEY")
    if key_path and os.path.exists(key_path):
        os.chmod(key_path, "0o600")  
        
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database="postgres",
        user="postgres",
        password=os.getenv("DB_PASSWORD"),
        sslmode="verify-ca",
        sslrootcert=os.getenv("DB_SSL_CA"),
        sslcert=os.getenv("DB_SSL_CERT"),
        sslkey=key_path
    )
    conn.autocommit = True
    return conn


def check_if_article_saved(title: str):
    """
    Checks the database to see if we have already saved this article title.
    Returns True if found, False otherwise.
    """

    conn = _get_conn()
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


def _embed(text: str) -> np.ndarray:
    result = rg.genai_client.models.embed_content(model=rg.EMBEDDING_MODEL, contents=text)
    return np.array(result.embeddings[0].values)
 
 
def _corpus_centroid():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT abstract_vector FROM websearch_articles "
        "WHERE status = 'confirmed' AND abstract_vector IS NOT NULL"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        return None
        
    float_vectors = []
    for row in rows:
        val = row[0]
        # If pgvector returned the data as a string
        if isinstance(val, str):
            cleaned = val.strip("[]")
            if cleaned:
                # Convert the comma-separated string of floats into a list of floats
                vector_list = [float(x.strip()) for x in cleaned.split(",")]
                float_vectors.append(vector_list)
        # If it was returned as a list/tuple of floats
        elif isinstance(val, (list, tuple)):
            float_vectors.append(list(val))
        # If it is already a NumPy array
        elif isinstance(val, np.ndarray):
            float_vectors.append(val.tolist())
            
    if not float_vectors:
        return None
        
    return np.mean(np.array(float_vectors), axis=0)


def gate_and_save(title: str, link: str, snippet: str):
    """
    Classifies a candidate article for topic relevance before saving it.
    Runs an LLM relevance check plus an embedding similarity check against a
    lready-confirmed papers, and routes disagreements to a review queue 
    instead of guessing.
    """
    if check_if_article_saved(title):
        return f"Already saved: {title}"

    cleaned_link = clean_url(link)
    check = rg.classify_relevance(title, snippet)
 
    vector = _embed(f"{title} {snippet}")
    centroid = _corpus_centroid()
    if centroid is None:
        similarity = 1.0  # no confirmed corpus yet to compare against
    else:
        norm_v = np.linalg.norm(vector)
        norm_c = np.linalg.norm(centroid)
        if norm_v == 0 or norm_c == 0:
            similarity = 0.0  # Prevent division-by-zero crash
        else:
            similarity = float(np.dot(vector, centroid) / (norm_v * norm_c))
 
    if check.is_primary_subject and check.confidence >= rg.CONFIDENCE_THRESHOLD and similarity >= rg.SIMILARITY_THRESHOLD:
        status = "confirmed"
    elif not check.is_primary_subject and check.confidence >= rg.CONFIDENCE_THRESHOLD:
        return f"Rejected (not relevant): {title} - {check.reasoning}"
    else:
        status = "needs_review"
 
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO websearch_articles (title, link, abstract, abstract_vector, status, relevance_reasoning) "
            "VALUES (%s, %s, %s, %s::vector, %s, %s)",
            (title, cleaned_link, snippet, vector.tolist(), status,
             f"{check.reasoning} (organism: {check.organism}, topic: {check.matched_topic}, sim: {similarity:.2f})"),
        )
        conn.commit()
        return f"Saved as '{status}': {title}"
    except Exception as e:
        print(f"[DATABASE ERROR] Failed to save {title}. Error: {str(e)}")
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

