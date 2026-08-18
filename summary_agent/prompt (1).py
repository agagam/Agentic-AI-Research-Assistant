from langchain_core.prompts import ChatPromptTemplate

SUMMARY_PROMPT = ChatPromptTemplate.from_template(
    """You are a plant genomics research assistant. Based ONLY on the excerpts
below (from Arabidopsis thaliana research papers), write a structured summary
for the topic: "{topic}"
 
Include, if present in the excerpts:
- Key findings
- Genes / mutants / pathways studied
- Methods used - especially highlight NGS technologies, such as RNA-seq, ChIP-seq, ATAC-seq, etc.
- Open questions or limitations noted by the authors
 
If the excerpts don't contain enough information to answer, say so explicitly
rather than inferring beyond what's given.
 
Excerpts:
{context}
"""
)