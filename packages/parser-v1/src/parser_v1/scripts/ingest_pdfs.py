"""Ingest prescribing info PDFs into ChromaDB with section-aware chunking."""

import os
import sys
import time
from pathlib import Path

from loguru import logger
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

import chromadb
from dotenv import load_dotenv
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from parser_v1.config import COLLECTION_NAME
from parser_v1.scripts.drug_metadata import get_drug_metadata
from parser_v1.scripts.pdf_section_parser import parse_pdf_into_sections

# Paths
PRESCRIBING_INFO_DIR = Path.cwd() / "prescribing_info"
CHROMA_DB_DIR = Path.cwd() / "chroma_db"


_MAX_RETRY_ATTEMPTS = 6


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Return True if the exception looks like an API rate-limit error."""
    msg = str(exc).lower()
    if (
        "429" in msg
        or "rate limit" in msg
        or "rate_limit" in msg
        or "too many requests" in msg
    ):
        return True
    if exc.__cause__:
        return _is_rate_limit_error(exc.__cause__)
    return False


def _log_retry(rs: RetryCallState) -> None:
    """Log retry attempts via loguru before sleeping."""
    wait = rs.next_action.sleep if rs.next_action else 0
    logger.warning(
        "Rate limit hit — retrying in {wait:.1f}s (attempt {attempt}/{max_attempts})",
        wait=wait,
        attempt=rs.attempt_number,
        max_attempts=_MAX_RETRY_ATTEMPTS,
    )


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


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=1, min=10, max=120),
    stop=stop_after_attempt(_MAX_RETRY_ATTEMPTS),
    before_sleep=_log_retry,
    reraise=True,
)
def _run_pipeline_with_retry(pipeline: IngestionPipeline, documents: list) -> list:
    """Run the ingestion pipeline with retry on rate-limit errors."""
    return pipeline.run(documents=documents)


def main():
    load_dotenv()

    cohere_key = os.environ.get("COHERE_API_KEY")
    if not cohere_key:
        print("ERROR: COHERE_API_KEY not set. Check your .env file.", file=sys.stderr)
        sys.exit(1)

    # Setup ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # Find already-ingested PDFs by querying source_file metadata
    existing_meta = chroma_collection.get(include=["metadatas"])
    ingested_files: set[str] = set()
    if existing_meta["metadatas"]:
        ingested_files = {m.get("source_file", "") for m in existing_meta["metadatas"]}
    ingested_files.discard("")

    # Build pipeline
    pipeline = build_pipeline(vector_store, api_key=cohere_key)

    # Process each PDF — skip already-ingested ones
    all_pdf_files = sorted(PRESCRIBING_INFO_DIR.glob("*.pdf"))
    pdf_files = [f for f in all_pdf_files if f.name not in ingested_files]
    skipped = len(all_pdf_files) - len(pdf_files)
    print(
        f"Found {len(all_pdf_files)} PDFs total, {skipped} already ingested, {len(pdf_files)} to process\n"
    )

    xml_files = sorted(PRESCRIBING_INFO_DIR.glob("*.xml"))
    if xml_files:
        print(
            f"Warning: Found {len(xml_files)} XML fallback file(s) — not ingested: {[f.name for f in xml_files]}\n"
        )

    total_nodes = 0
    failed = []
    md_path = Path.cwd() / "top_50_drugs.md"

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {pdf_path.name}...")
        start = time.time()

        try:
            # Get drug metadata
            drug_meta = get_drug_metadata(pdf_path.name, md_path=md_path)

            # Parse PDF into section-level documents with metadata
            documents = parse_pdf_into_sections(pdf_path, base_metadata=drug_meta)

            # Run ingestion pipeline (chunk + embed + store)
            nodes = _run_pipeline_with_retry(pipeline, documents)
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
    print(f"PDFs processed this run: {len(pdf_files) - len(failed)}/{len(pdf_files)}")
    print(f"PDFs previously ingested: {skipped}")
    print(f"Chunks added this run:  {total_nodes}")
    print(f"ChromaDB location:      {CHROMA_DB_DIR}")
    print(f"Collection:             {COLLECTION_NAME}")

    if failed:
        print(f"\nFailed ({len(failed)}):")
        for name, err in failed:
            print(f"  {name}: {err}")

    # Verify
    count = chroma_collection.count()
    print(f"\nChromaDB collection count: {count}")


if __name__ == "__main__":
    main()
