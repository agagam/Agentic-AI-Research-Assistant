import os

GCP_PROJECT = os.environ.get("GCP_PROJECT", "")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
PDF_BUCKET = os.environ.get("PDF_BUCKET", "arabidopsis-pdfs")