"""Ingest prescribing info PDFs into ChromaDB with section-aware chunking."""

import os
import sys
import time
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

# Add project root to path for src imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import COLLECTION_NAME
from src.drug_metadata import get_drug_metadata
from src.pdf_section_parser import parse_pdf_into_sections

# Paths
PRESCRIBING_INFO_DIR = PROJECT_ROOT / "prescribing_info"
CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"


def build_pipeline(vector_store: ChromaVectorStore, api_key: str) -> IngestionPipeline:
    """Build the LlamaIndex ingestion pipeline."""
    embed_model = CohereEmbedding(
        api_key=api_key,
        model_name="embed-v4.0",
        input_type="search_document",
    )

    return IngestionPipeline(
        transformations=[
            SentenceSplitter(chunk_size=1024, chunk_overlap=128),
            embed_model,
        ],
        vector_store=vector_store,
    )


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    cohere_key = os.environ.get("COHERE_API_KEY")
    if not cohere_key:
        print("ERROR: COHERE_API_KEY not set. Check your .env file.", file=sys.stderr)
        sys.exit(1)

    # Setup ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    # Delete existing collection if re-ingesting
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # Build pipeline
    pipeline = build_pipeline(vector_store, api_key=cohere_key)

    # Process each PDF
    pdf_files = sorted(PRESCRIBING_INFO_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs to process\n")

    xml_files = sorted(PRESCRIBING_INFO_DIR.glob("*.xml"))
    if xml_files:
        print(
            f"Warning: Found {len(xml_files)} XML fallback file(s) — not ingested: {[f.name for f in xml_files]}\n"
        )

    total_nodes = 0
    failed = []

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {pdf_path.name}...")
        start = time.time()

        try:
            # Get drug metadata
            drug_meta = get_drug_metadata(pdf_path.name)

            # Parse PDF into section-level documents with metadata
            documents = parse_pdf_into_sections(pdf_path, base_metadata=drug_meta)

            # Run ingestion pipeline (chunk + embed + store)
            nodes = pipeline.run(documents=documents)
            elapsed = time.time() - start

            print(
                f"  -> {len(documents)} sections -> {len(nodes)} chunks ({elapsed:.1f}s)"
            )
            total_nodes += len(nodes)

        except Exception as e:
            elapsed = time.time() - start
            print(f"  -> ERROR: {e} ({elapsed:.1f}s)")
            failed.append((pdf_path.name, str(e)))

    # Summary
    print(f"\n{'=' * 60}")
    print("INGESTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total PDFs processed: {len(pdf_files) - len(failed)}/{len(pdf_files)}")
    print(f"Total chunks stored:  {total_nodes}")
    print(f"ChromaDB location:    {CHROMA_DB_DIR}")
    print(f"Collection:           {COLLECTION_NAME}")

    if failed:
        print(f"\nFailed ({len(failed)}):")
        for name, err in failed:
            print(f"  {name}: {err}")

    # Verify
    count = chroma_collection.count()
    print(f"\nChromaDB collection count: {count}")


if __name__ == "__main__":
    main()
