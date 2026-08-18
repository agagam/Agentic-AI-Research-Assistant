import io
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from dataclasses import dataclass
from google.cloud import storage
import config




### --- Inserting into the database ---

def _get_conn():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database="postgres",
        user="postgres",
        password=os.getenv("DB_PASSWORD"),
        sslmode="verify-ca",
        sslrootcert=os.getenv("DB_SSL_CA"),
        sslcert=os.getenv("DB_SSL_CERT"),
        sslkey=os.getenv("DB_SSL_KEY")
    )
    conn.autocommit = True
    return conn

def insert_chunks(rows: Iterable[dict]) -> int:
    """
    rows: iterable of dicts with keys
        source_pdf, page_number, chunk_text, embedding, publication_id (optional)
    Returns number of rows inserted.
    """
    rows = list(rows)
    if not rows:
        return 0
    with _get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO pdf_chunks
                (publication_id, source_pdf, page_number, chunk_text, embedding, created_at)
            VALUES %s
            """,
            [
                (
                    r.get("publication_id"),
                    r["source_pdf"],
                    r.get("page_number"),
                    r["chunk_text"],
                    r["embedding"],
                    dt.datetime.utcnow(),
                )
                for r in rows
            ],
        )
    return len(rows)

def already_saved(source_pdf: str) -> bool:
    """Checks the database if the embeddings are already saved"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pdf_chunks WHERE source_pdf = %s LIMIT 1;", (source_pdf,)
        )
        return cur.fetchone() is not None


### --- extracting PDF data ---

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=120, separators=["\n\n", "\n", ". ", " "]
)

@dataclass
class PdfPage:
    page_number: int
    text: str
 
 
def _extract_pages(pdf_bytes: bytes) -> list[PdfPage]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(PdfPage(page_number=i + 1, text=text))
    return pages
 
 
def save_new_pdfs() -> int:
    """Scan the GCS bucket, chunk + embed any PDF not already in pdf_chunks."""
    client = storage.Client(project=config.GCP_PROJECT)
    bucket = client.bucket(config.PDF_BUCKET)
 
    total_chunks = 0
    for blob in bucket.list_blobs():
        if not blob.name.lower().endswith(".pdf"):
            continue
        if db.already_ingested(blob.name):
            continue
 
        pdf_bytes = blob.download_as_bytes()
        pages = _extract_pages(pdf_bytes)
 
        rows = []
        for page in pages:
            for chunk in splitter.split_text(page.text):
                rows.append(
                    {
                        "source_pdf": blob.name,
                        "page_number": page.page_number,
                        "chunk_text": chunk,
                        "embedding": embeddings.embed_query(chunk),
                    }
                )
        inserted = insert_chunks(rows)
        total_chunks += inserted
        print(f"Ingested {blob.name}: {inserted} chunks")
 
    return total_chunks
