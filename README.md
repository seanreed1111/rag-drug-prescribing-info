# Drug Prescribing Information Dataset

A collection of FDA-approved prescribing information (package inserts) for the top 50 best-selling drugs in the United States, intended for use in retrieval-augmented generation (RAG) experiments.

## Directory Structure

```
drug-prescribing-info/
├── README.md                  # This file
├── top_50_drugs.md            # Ranked list of the top 50 drugs with sales data and indications
├── pyproject.toml             # uv workspace root
├── prescribing_info/          # 50 FDA prescribing information PDFs (78 MB total)
│   ├── keytruda_prescribing_info.pdf
│   ├── ozempic_prescribing_info.pdf
│   └── ...
├── chroma_db/                 # ChromaDB vector store (local, gitignored)
├── packages/
│   ├── parser-v1/             # PDF parsing, embedding, and query package
│   │   └── src/parser_v1/
│   │       ├── config.py
│   │       ├── scripts/
│   │       │   ├── download_prescribing_info.py  # Downloads PDFs for drugs ranked 1-20
│   │       │   ├── download_remaining.py         # Downloads PDFs for drugs ranked 21-50
│   │       │   ├── drug_metadata.py              # Drug name/metadata helpers
│   │       │   ├── ingest_pdfs.py                # Ingests PDFs into ChromaDB
│   │       │   ├── pdf_section_parser.py         # Section-aware PDF chunker
│   │       │   └── query.py                      # Query the ChromaDB vector store
│   │       └── tests/
│   └── parser-v2/             # Next-generation parser (in development)
├── plan/                      # Implementation plans and design docs
└── thoughts/                  # Research notes and exploratory docs
```

## Data Contents

- **top_50_drugs.md** -- The top 50 best-selling drugs ranked by revenue, with brand name, generic name, manufacturer, sales figures, and a summary of approved indications/conditions.
- **prescribing_info/** -- One PDF per drug containing the full FDA-approved prescribing information (also known as the package insert or drug label). These include dosage, indications, contraindications, warnings, adverse reactions, clinical pharmacology, and more.

## Data Sources

| Source | What it provides |
|--------|-----------------|
| [Drug Discovery Trends -- Top 25 drugs by sales: 2025 H1](https://www.drugdiscoverytrends.com/top-25-drugs-by-sales-2025-h1/) | H1 2025 sales data for ranks 1-20 |
| [Drug Discovery Trends -- 2024 blockbusters: Top 50 by sales](https://www.drugdiscoverytrends.com/2024s-blockbusters-top-50-pharmaceuticals-by-sales/) | Full-year 2024 sales data for ranks 21-50 |
| [Xtalks -- Top 50 Best-Selling Drugs to Watch in 2025](https://xtalks.com/top-50-best-selling-drugs-to-watch-in-2025-insights-from-2024-sales-data-4343/) | Drug indications and therapeutic areas |
| [DailyMed (NIH/NLM)](https://dailymed.nlm.nih.gov/) | FDA-approved prescribing information PDFs |

## Reproducing the Downloads

The scripts use the DailyMed REST API (no API key required) to look up each drug and download its prescribing information PDF. To re-download:

```bash
uv run python packages/parser-v1/src/parser_v1/scripts/download_prescribing_info.py   # drugs 1-20
uv run python packages/parser-v1/src/parser_v1/scripts/download_remaining.py           # drugs 21-50
```

PDFs are saved to `prescribing_info/`. The scripts include a 1-second delay between requests to be respectful to the DailyMed API.

## ChromaDB Vector Store

The PDFs are ingested into a local ChromaDB collection (`chroma_db/`) using section-aware chunking and Cohere embed-v4 embeddings. See `packages/parser-v1/src/parser_v1/scripts/ingest_pdfs.py` to run ingestion and `packages/parser-v1/src/parser_v1/scripts/query.py` to query the store.

### parser-v1

`packages/parser-v1` is the ingestion and retrieval package. It parses each PDF into FDA label sections (e.g. `5 WARNINGS AND PRECAUTIONS`, `12.1 Mechanism of Action`), attaches structured drug metadata to every section, then chunks each section with a `SentenceSplitter` (1024-token chunks, 128-token overlap) and embeds with Cohere `embed-v4.0`. Chunks are stored in ChromaDB with metadata fields (`brand_name`, `generic_name`, `therapeutic_area`, `fda_section`, `fda_subsection`) that allow filtered retrieval at query time. The ingestion script is idempotent — it skips already-ingested PDFs and retries on Cohere rate-limit errors with exponential backoff.

See [`packages/parser-v1/README.md`](packages/parser-v1/README.md) for full documentation including pipeline diagrams, chunking parameters, and metadata schema.

### PDFs Ingested into ChromaDB

48 of 50 PDFs have been embedded and stored:

| Drug (Brand) | File | Sections | Chunks |
|---|---|---|---|
| Biktarvy | `biktarvy_prescribing_info.pdf` | 15 | 47 |
| Comirnaty | `comirnaty_prescribing_info.pdf` | 13 | 66 |
| Cosentyx | `cosentyx_prescribing_info.pdf` | 15 | 55 |
| Darzalex | `darzalex_prescribing_info.pdf` | 15 | 60 |
| Dupixent | `dupixent_prescribing_info.pdf` | 18 | 90 |
| Eliquis | `eliquis_prescribing_info.pdf` | 16 | 40 |
| Entresto | `entresto_prescribing_info.pdf` | 18 | 36 |
| Entyvio | `entyvio_prescribing_info.pdf` | 16 | 42 |
| Eylea | `eylea_prescribing_info.pdf` | 14 | 26 |
| Farxiga | `farxiga_prescribing_info.pdf` | 15 | 53 |
| Gardasil | `gardasil_prescribing_info.pdf` | 18 | 53 |
| Hemlibra | `hemlibra_prescribing_info.pdf` | 15 | 38 |
| Humira | `humira_prescribing_info.pdf` | 21 | 77 |
| Ibrance | `ibrance_prescribing_info.pdf` | 18 | 36 |
| Imbruvica | `imbruvica_prescribing_info.pdf` | 16 | 53 |
| Imfinzi | `imfinzi_prescribing_info.pdf` | 18 | 71 |
| Invega Sustenna | `invega_sustenna_prescribing_info.pdf` | 22 | 53 |
| Jardiance | `jardiance_prescribing_info.pdf` | 16 | 51 |
| Lynparza | `lynparza_prescribing_info.pdf` | 17 | 53 |
| Mounjaro | `mounjaro_prescribing_info.pdf` | 18 | 64 |
| Ocrevus | `ocrevus_prescribing_info.pdf` | 14 | 28 |
| OFEV | `ofev_prescribing_info.pdf` | 15 | 35 |
| Orencia | `orencia_prescribing_info.pdf` | 16 | 43 |
| Ozempic | `ozempic_prescribing_info.pdf` | 20 | 53 |
| Paxlovid | `paxlovid_prescribing_info.pdf` | 15 | 52 |
| Perjeta | `perjeta_prescribing_info.pdf` | 13 | 34 |
| Pomalyst | `pomalyst_prescribing_info.pdf` | 17 | 42 |
| Prevnar | `prevnar_prescribing_info.pdf` | 14 | 52 |
| Prolia | `prolia_prescribing_info.pdf` | 13 | 33 |
| Revlimid | `revlimid_prescribing_info.pdf` | 16 | 75 |
| Rinvoq | `rinvoq_prescribing_info.pdf` | 14 | 80 |
| Rybelsus | `rybelsus_prescribing_info.pdf` | 21 | 41 |
| Shingrix | `shingrix_prescribing_info.pdf` | 18 | 35 |
| Skyrizi | `skyrizi_prescribing_info.pdf` | 14 | 71 |
| Stelara | `stelara_prescribing_info.pdf` | 18 | 46 |
| Tagrisso | `tagrisso_prescribing_info.pdf` | 17 | 46 |
| Tecentriq | `tecentriq_prescribing_info.pdf` | 13 | 74 |
| Tremfya | `tremfya_prescribing_info.pdf` | 14 | 57 |
| Trikafta | `trikafta_prescribing_info.pdf` | 15 | 54 |
| Trulicity | `trulicity_prescribing_info.pdf` | 16 | 57 |
| Vabysmo | `vabysmo_prescribing_info.pdf` | 13 | 18 |
| Verzenio | `verzenio_prescribing_info.pdf` | 15 | 39 |
| Vyndaqel | `vyndaqel_prescribing_info.pdf` | 2 | 13 |
| Wegovy | `wegovy_prescribing_info.pdf` | 15 | 61 |
| Xarelto | `xarelto_prescribing_info.pdf` | 16 | 52 |
| Xolair | `xolair_prescribing_info.pdf` | 17 | 58 |
| Xtandi | `xtandi_prescribing_info.pdf` | 20 | 41 |
| Zepbound | `zepbound_prescribing_info.pdf` | 16 | 70 |

**Total: 2,424 chunks across 48 drugs**

> **Note:** 2 PDFs (Keytruda, Opdivo) failed to ingest — they exceeded the Cohere trial API rate limit (100K tokens/min) even after 6 retry attempts with exponential backoff. To ingest these, wait for the per-minute token window to reset and re-run `uv run python -m parser_v1.scripts.ingest_pdfs` (the script will skip the 48 already-ingested PDFs). To ingest all 50 reliably, upgrade your Cohere account.

## Date Collected

February 2026
