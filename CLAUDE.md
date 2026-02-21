# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG (Retrieval-Augmented Generation) dataset of FDA-approved prescribing information for the top 50 best-selling drugs in the United States. The PDFs in `prescribing_info/` are the primary data assets; everything else supports collecting and working with them.

## Key Commands

```bash
# Re-download all prescribing info PDFs from DailyMed
python src/scripts/download_prescribing_info.py   # drugs ranked 1-20
python src/scripts/download_remaining.py           # drugs ranked 21-50

# Manage dependencies
uv add <package>
uv sync
```

## Important: Package Management

- NEVER modify pyproject.toml to add new dependencies to a project.
- **Always use `uv add <package>`** to add new dependencies instead. This ensures you get the latest compatible versions.
- Run `date -Iseconds` to check the current date before suggesting Python packages or versions.
- Do not assume package versions do not exist based on training data—always verify against `uv.lock` and `pyproject.toml` in the repository, which reflect actually working versions.


## Architecture

- **`prescribing_info/`** — 50 FDA prescribing information PDFs (~78 MB), one per drug, named `{brand}_prescribing_info.pdf`
- **`top_50_drugs.md`** — Reference table mapping rank, brand/generic names, manufacturers, sales figures, and indications
- **`src/scripts/`** — Download scripts that use the [DailyMed REST API](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm) (no API key needed). They look up each drug's set ID, then download the PDF. Falls back to XML if PDF is unavailable. 1-second delay between requests.
- **`src/tests/`** — pytest test suite for the library modules in `src/`.

## Data Sources

- Drug rankings/sales: Drug Discovery Trends (H1 2025 + 2024 annual)
- Drug indications: Xtalks
- Prescribing info PDFs: DailyMed (NIH/NLM)
