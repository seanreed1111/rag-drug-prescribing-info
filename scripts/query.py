"""Query the drug prescribing info vector store."""

import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import COLLECTION_NAME

CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    cohere_key = os.environ.get("COHERE_API_KEY")
    if not cohere_key:
        print("ERROR: COHERE_API_KEY not set. Check your .env file.", file=sys.stderr)
        sys.exit(1)

    # Parse query from command line
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
    else:
        query_text = "What are the warnings and precautions for Keytruda?"

    print(f"Query: {query_text}\n")

    # Load ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    chroma_collection = chroma_client.get_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    print(f"Collection '{COLLECTION_NAME}' loaded ({chroma_collection.count()} chunks)\n")

    # Create index with Cohere embeddings (search_query mode for retrieval)
    embed_model = CohereEmbedding(
        api_key=cohere_key,
        model_name="embed-v4.0",
        input_type="search_query",
    )

    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model,
    )

    # Retrieve top-5 chunks (no LLM synthesis - just retrieval)
    retriever = index.as_retriever(similarity_top_k=5)
    results = retriever.retrieve(query_text)

    print(f"Top {len(results)} results:\n")
    for i, node_with_score in enumerate(results, 1):
        node = node_with_score.node
        score = node_with_score.score
        meta = node.metadata
        print(f"--- Result {i} (score: {score:.4f}) ---")
        print(f"  Drug:        {meta.get('brand_name', 'N/A')}")
        print(f"  Section:     {meta.get('fda_section', 'N/A')}")
        print(f"  Subsection:  {meta.get('fda_subsection', 'N/A') or 'N/A'}")
        print(f"  Therapeutic: {meta.get('therapeutic_area', 'N/A')}")
        print(f"  Source:      {meta.get('source_file', 'N/A')}")
        print(f"  Text preview: {node.text[:200]}...")
        print()


if __name__ == "__main__":
    main()
