# parser-v1

PDF ingestion and embedding pipeline for FDA prescribing information. Parses the top-50 drug PDFs into section-aware chunks and stores them in a ChromaDB vector store for RAG retrieval.

## Overview

```mermaid
graph TD
    A["prescribing_info/*.pdf<br/>50 FDA label PDFs"] --> B["drug_metadata.py<br/>Look up drug registry"]
    A --> C["pdf_section_parser.py<br/>Extract + split by FDA section"]
    B --> D["LlamaIndex Document<br/>per section/subsection<br/>+ metadata"]
    C --> D
    D --> E["SentenceSplitter<br/>chunk_size=1024<br/>chunk_overlap=128"]
    E --> F["CohereEmbedding<br/>embed-v4.0"]
    F --> G[("ChromaDB<br/>drug_prescribing_info<br/>collection")]
```

## Ingestion Pipeline (`ingest_pdfs.py`)

The entry point. For each PDF in `prescribing_info/`:

```mermaid
graph TD
    START["ingest_pdfs.py main"] --> CHROMA["Connect to ChromaDB<br/>get_or_create_collection"]
    CHROMA --> EXISTING["Query existing metadata<br/>collect ingested source_file names"]
    EXISTING --> PDFS["Glob prescribing_info/*.pdf"]
    PDFS --> FILTER["Filter out already-ingested PDFs<br/>idempotent reruns"]
    FILTER --> LOOP{"For each PDF"}
    LOOP --> META["get_drug_metadata<br/>look up brand, generic,<br/>manufacturer, rank, area"]
    META --> PARSE["parse_pdf_into_sections<br/>N section Documents"]
    PARSE --> PIPELINE["IngestionPipeline.run<br/>SentenceSplitter + Cohere + ChromaDB"]
    PIPELINE --> RETRY{"HTTP 429?"}
    RETRY -- Yes --> BACKOFF["tenacity exponential backoff<br/>min 10s, max 120s<br/>up to 6 attempts"]
    BACKOFF --> PIPELINE
    RETRY -- No --> NEXT["next PDF"]
    NEXT --> LOOP
    LOOP --> DONE["Print summary<br/>total chunks, failures"]
```

### Running

```bash
COHERE_API_KEY=<key> uv run python -m parser_v1.scripts.ingest_pdfs
```

Or with a `.env` file containing `COHERE_API_KEY`.

## Document Ingestion (`pdf_section_parser.py`)

```mermaid
graph TD
    P["PDF file"] --> R["pypdf PdfReader<br/>extract text page-by-page"]
    R --> T["Full text string"]
    T --> H["Regex scan for FDA section headers<br/>e.g. 5 WARNINGS AND PRECAUTIONS<br/>or 12.1 Mechanism of Action"]
    H --> D["Deduplicate headers<br/>keep last occurrence<br/>discards TOC entries"]
    D --> S{"Sections found?"}
    S -- No --> FB["Fallback: single Document<br/>for entire PDF"]
    S -- Yes --> SL["Slice text between<br/>consecutive section headers"]
    SL --> SK["Skip sections under 20 chars"]
    SK --> MD["Attach metadata per Document"]
    MD --> OUT["List of Documents"]
```

### TOC Deduplication

FDA labels begin with a table of contents that lists every section header before the body content. Without deduplication, every section would appear twice. The parser keeps the **last** occurrence of each section number, which is always the actual body text.

```mermaid
graph LR
    RAW["Raw header matches<br/>1 INDICATIONS at pos 120<br/>5 WARNINGS at pos 340<br/>1 INDICATIONS at pos 890<br/>5 WARNINGS at pos 1420"] --> DEDUP["Deduplicate<br/>keep last index per number"]
    DEDUP --> CLEAN["Body-only headers<br/>1 INDICATIONS at pos 890<br/>5 WARNINGS at pos 1420"]
```

### Section Detection

Headers are matched with this regex pattern:

```
^\d{1,2}(?:\.\d{1,2})?\s+[A-Z][A-Z &,/\-]{2,}.*$
```

This captures both top-level sections (`5 WARNINGS AND PRECAUTIONS`) and subsections (`5.1 Immune-Mediated Pneumonitis`).

### Document Hierarchy

Each PDF produces a two-level document tree. Subsection documents inherit the parent section label as `fda_section`.

```mermaid
graph TD
    PDF["keytruda_prescribing_info.pdf"] --> S5["fda_section: 5 WARNINGS AND PRECAUTIONS<br/>fda_subsection: empty"]
    PDF --> S51["fda_section: 5 WARNINGS AND PRECAUTIONS<br/>fda_subsection: 5.1 Immune-Mediated Pneumonitis"]
    PDF --> S52["fda_section: 5 WARNINGS AND PRECAUTIONS<br/>fda_subsection: 5.2 Immune-Mediated Colitis"]
    PDF --> S12["fda_section: 12 CLINICAL PHARMACOLOGY<br/>fda_subsection: empty"]
    PDF --> S121["fda_section: 12 CLINICAL PHARMACOLOGY<br/>fda_subsection: 12.1 Mechanism of Action"]
```

Each `Document` carries:

| Metadata key | Example value | Included in embedding | Included in LLM context |
|---|---|---|---|
| `source_file` | `keytruda_prescribing_info.pdf` | No | Yes |
| `fda_section` | `5 WARNINGS AND PRECAUTIONS` | Yes | Yes |
| `fda_subsection` | `5.1 Immune-Mediated Pneumonitis` | Yes | Yes |
| `brand_name` | `Keytruda` | Yes | Yes |
| `generic_name` | `pembrolizumab` | Yes | Yes |
| `manufacturer` | `Merck` | Yes | Yes |
| `rank` | `1` | No | No |
| `indications` | `Melanoma, NSCLC, ...` | Yes | Yes |
| `therapeutic_area` | `Oncology` | Yes | Yes |

## Drug Metadata (`drug_metadata.py`)

```mermaid
graph TD
    MD["top_50_drugs.md<br/>markdown table"] --> PARSE["Regex row parser<br/>rank, brand, generic,<br/>manufacturer, indications"]
    PARSE --> STEM["Derive filename stem<br/>Keytruda -> keytruda<br/>Invega Sustenna/Trinza -> invega_sustenna"]
    STEM --> REG["Module-level registry dict<br/>keyed by stem"]
    REG --> LOOKUP{"PDF filename lookup<br/>strip _prescribing_info.pdf"}
    LOOKUP -- Found --> FULL["Full metadata dict"]
    LOOKUP -- Not found --> FALLBACK["Minimal fallback<br/>rank=0, area=Other"]
    FULL --> CLASS["Therapeutic area classification<br/>keyword match on indications"]
    CLASS --> OUT["brand_name, generic_name,<br/>manufacturer, rank,<br/>indications, therapeutic_area"]
```

### Therapeutic Area Classification

```mermaid
graph LR
    IND["indications text"] --> KW{"keyword match"}
    KW --> ONC["Oncology<br/>cancer, tumor, carcinoma..."]
    KW --> IMM["Immunology<br/>psoriasis, arthritis, crohn..."]
    KW --> MET["Metabolic/Endocrine<br/>diabetes, obesity..."]
    KW --> CV["Cardiovascular<br/>heart failure, stroke..."]
    KW --> NEU["Neurology<br/>multiple sclerosis..."]
    KW --> INF["Infectious Disease<br/>hiv, covid, vaccine..."]
    KW --> OPH["Ophthalmology<br/>macular degeneration..."]
    KW --> RES["Respiratory<br/>asthma, copd..."]
    KW --> OTH["Other"]
```

## Chunking Strategy

```mermaid
graph LR
    DOC["Section Document<br/>e.g. 5.1 Immune-Mediated Pneumonitis<br/>500-3000 tokens"] --> SS["SentenceSplitter<br/>chunk_size: 1024 tokens<br/>chunk_overlap: 128 tokens"]
    SS --> C1["Chunk 1<br/>+ inherited metadata"]
    SS --> C2["Chunk 2<br/>+ inherited metadata"]
    SS --> CN["Chunk N<br/>+ inherited metadata"]
    C1 --> EMB["Cohere embed-v4.0<br/>search_document mode"]
    C2 --> EMB
    CN --> EMB
    EMB --> DB[("ChromaDB<br/>vector store")]
```

| Parameter | Value | Rationale |
|---|---|---|
| Chunk size | 1024 tokens | Fits dense clinical text with enough context per chunk |
| Chunk overlap | 128 tokens | Preserves sentence continuity at boundaries |
| Splitter | `SentenceSplitter` | Respects sentence boundaries; avoids mid-sentence cuts |
| Embedding model | `embed-v4.0` (Cohere) | High-quality retrieval embeddings; `search_document` input type |
| Vector store | ChromaDB (persistent) | Local, file-based; no external service required |

The two-level split strategy — **section first, then sentence-boundary chunks** — keeps the FDA section and subsection labels as metadata on every chunk. This enables hybrid retrieval filtering (e.g., "search only within section 5 WARNINGS" or "filter by therapeutic_area=Oncology") without re-parsing.

## Query / Retrieval (`query.py`)

```mermaid
graph TD
    Q["Query string<br/>e.g. What are the warnings for Keytruda?"] --> EMB["CohereEmbedding<br/>embed-v4.0<br/>search_query mode"]
    EMB --> IDX["VectorStoreIndex<br/>from ChromaDB vector store"]
    IDX --> RET["Retriever<br/>similarity_top_k=5"]
    RET --> RES["Top-5 NodeWithScore results"]
    RES --> OUT["For each result:<br/>score, brand_name, fda_section,<br/>fda_subsection, therapeutic_area,<br/>text preview"]
```

Note the asymmetric embedding modes: documents are ingested with `search_document` and queries use `search_query`. Cohere's `embed-v4.0` is trained to maximize similarity between these two modes.

## Project Structure

```
packages/parser-v1/
├── src/parser_v1/
│   ├── config.py                  # COLLECTION_NAME constant
│   ├── scripts/
│   │   ├── ingest_pdfs.py         # Main pipeline entry point
│   │   ├── pdf_section_parser.py  # PDF -> section Documents
│   │   ├── drug_metadata.py       # Metadata registry from top_50_drugs.md
│   │   ├── query.py               # Query/retrieval helpers
│   │   └── download_*.py          # PDF download scripts (from DailyMed)
│   └── tests/
│       ├── test_ingest_pdfs.py
│       ├── test_section_parser.py
│       └── test_drug_metadata.py
└── pyproject.toml
```
