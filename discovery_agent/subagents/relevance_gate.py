from google import genai
from pydantic import BaseModel, Field
from google.genai import types


genai_client = genai.Client()
CLASSIFIER_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "text-embedding-005"
 
TOPICS = [
    "Arabidopsis thaliana LHP1 (LIKE HETEROCHROMATIN PROTEIN 1)",
    "Arabidopsis thaliana Polycomb (PRC1/PRC2, chromatin repression)",
    "Arabidopsis thaliana H1 (linker histone H1, 3H1)",
]
CONFIDENCE_THRESHOLD = 0.8
SIMILARITY_THRESHOLD = 0.55
 
 
class RelevanceCheck(BaseModel):
    """
    """
    organism: str = Field(description="The primary organism this paper studies")
    matched_topic: str = Field(description="Which target topic this paper matches, or 'none'")
    is_primary_subject: bool = Field(
        description="True only if the paper's actual subject is one of the target "
                     "topics in Arabidopsis thaliana specifically - not the same "
                     "gene/protein family studied in a different organism, and not "
                     "just mentioned in passing"
    )
    confidence: float = Field(description="0.0 to 1.0", ge=0.0, le=1.0)
    reasoning: str = Field(description="One sentence explaining the decision")
 
 
def classify_relevance(title: str, snippet: str) -> RelevanceCheck:
    topic_list = "\n".join(f"- {t}" for t in TOPICS)
    prompt = (
        f"Paper title: {title}\nContext: {snippet}\n\n"
        f"Target topics (a match on ANY one counts as relevant):\n{topic_list}\n\n"
        "Does this paper's primary subject match one of the target topics, "
        "specifically in Arabidopsis thaliana? Watch for false positives: the "
        "same gene family (e.g. CPP, LHP1-like, H1 homologs, PRC1/PRC2 "
        "components) studied in a different organism (peanut, rice, soybean, "
        "etc.) does NOT count, even though the terminology overlaps. Extract "
        "the organism explicitly."
    )
    response = genai_client.models.generate_content(
        model=CLASSIFIER_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RelevanceCheck,
        ),
    )
    return response.parsed
 
 
