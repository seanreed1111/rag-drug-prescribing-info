# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased] — 2026-02-20

### New Features

- **PDF Ingestion Pipeline**: Ingest FDA prescribing information PDFs into a ChromaDB vector store with `scripts/ingest_pdfs.py`. Supports structured section-level chunking for higher-quality retrieval.
- **RAG Query Interface**: Query the vector store with natural language using `scripts/query.py`. Returns relevant prescribing information passages with source attribution.
- **PDF Section Parser**: Automatically detects and extracts standard FDA label sections (Indications, Dosage, Warnings, etc.) from prescribing information PDFs.
- **Drug Metadata Extraction**: Extracts structured metadata (brand name, generic name, manufacturer, drug class) from PDF filenames and content for richer search context.

### Improvements

- Added `chroma_db/` and `.env` to `.gitignore` to keep vector database files and secrets out of version control.
- Added package management guidelines to `CLAUDE.md` to ensure reproducible dependency installation via `uv add`.
- Updated `README.md` with project overview, architecture description, and usage instructions.

---

## [0.1.0] — 2026-02-20 — Initial Release

### New Features

- **50 FDA Prescribing Information PDFs**: Downloaded from DailyMed (NIH/NLM) for the top 50 best-selling drugs in the US (~78 MB).
- **Download Scripts**: `scripts/download_prescribing_info.py` (drugs 1–20) and `scripts/download_remaining.py` (drugs 21–50) fetch PDFs via the DailyMed REST API with automatic fallback to XML.
- **Drug Reference Table**: `top_50_drugs.md` maps rank, brand/generic names, manufacturers, sales figures, and indications for all 50 drugs.
- **Project Scaffolding**: Full `uv`-managed Python project with `pyproject.toml`, Claude Code tooling (commands, agents, skills), and CI-ready structure.
