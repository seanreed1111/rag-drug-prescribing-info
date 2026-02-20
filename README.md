# Drug Prescribing Information Dataset

A collection of FDA-approved prescribing information (package inserts) for the top 50 best-selling drugs in the United States, intended for use in retrieval-augmented generation (RAG) experiments.

## Directory Structure

```
drug-prescribing-info/
├── README.md                  # This file
├── top_50_drugs.md            # Ranked list of the top 50 drugs with sales data and indications
├── prescribing_info/          # 50 FDA prescribing information PDFs (78 MB total)
│   ├── keytruda_prescribing_info.pdf
│   ├── ozempic_prescribing_info.pdf
│   └── ...
└── scripts/
    ├── download_prescribing_info.py   # Downloads prescribing info for drugs ranked 1-20
    └── download_remaining.py          # Downloads prescribing info for drugs ranked 21-50
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
python scripts/download_prescribing_info.py   # drugs 1-20
python scripts/download_remaining.py           # drugs 21-50
```

PDFs are saved to `prescribing_info/`. The scripts include a 1-second delay between requests to be respectful to the DailyMed API.

## Date Collected

February 2026
