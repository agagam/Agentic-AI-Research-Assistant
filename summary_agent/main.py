from langchain_google_vertexai import VertexAIEmbeddings, ChatVertexAI
import config
import tools
from prompt import SUMMARY_PROMPT

EMBEDDING_MODEL = "text-embedding-004"
LLM_MODEL = "gemini-2.0-flash"

embeddings = VertexAIEmbeddings(model_name=EMBEDDING_MODEL, project=config.GCP_PROJECT, location=config.GCP_REGION)
llm = ChatVertexAI(model_name=LLM_MODEL, project=config.GCP_PROJECT, location=config.GCP_REGION, temperature=0.2)

def summarize_topic(topic: str, top_k: int = 8) -> str:
    """RAG-style summarization: retrieve relevant chunks, then synthesize."""
    query_embedding = embeddings.embed_query(topic)
    results = tools.similarity_search(query_embedding, top_k=top_k)
 
    if not results:
        return f"No indexed PDF content found relevant to '{topic}'."
 
    context = "\n\n---\n\n".join(
        f"[{r['source_pdf']} p.{r['page_number']}] {r['chunk_text']}" for r in results
    )
    chain = SUMMARY_PROMPT | llm
    response = chain.invoke({"topic": topic, "context": context})
    return response.content
 
 
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
 
    command = sys.argv[1]
    if command == "save":
        n = tools.save_new_pdfs()
        print(f"Done. {n} new chunks embedded.")
    elif command == "summarize":
        topic = " ".join(sys.argv[2:]) or "recent findings"
        print(tools.summarize_topic(topic))
    else:
        print(f"Unknown command: {command}")
        print(__doc__)