# Metadata Enhancement Options for Drug Prescribing Info RAG

Date: 2026-02-20
Context: 50 FDA prescribing information PDFs from DailyMed, top-selling US drugs.
Goal: Enrich chunk-level and document-level metadata to improve retrieval precision and recall.

---

## What We Already Have

`top_50_drugs.md` gives us per-drug: rank, brand name, generic name, manufacturer, sales
figures, and a plain-text indications summary. Filenames follow `{brand}_prescribing_info.pdf`.
This is free metadata we can attach to every chunk just by parsing the filename and doing a
dict lookup — no extra processing required.

FDA prescribing labels follow a standardized structure (SPL — Structured Product Labeling),
so the same section hierarchy appears across all 50 documents. That structure is exploitable.

---

## Option 1 — Static metadata from `top_50_drugs.md` (free, do this first)

Attach the following to every chunk at index time, sourced entirely from the existing table:

```python
{
    "brand_name": "Keytruda",
    "generic_name": "pembrolizumab",
    "manufacturer": "Merck",
    "rank": 1,
    "sales_usd_m": 15161,
    "indications_summary": "Cancer immunotherapy (melanoma, NSCLC, ...)",
    "drug_type": "biologic",          # can be inferred from generic name suffix
    "source": "DailyMed FDA label",
}
```

**Why it helps:** Lets you answer "what does Merck make?" or "which rank-1 drug covers NSCLC?"
with a metadata filter instead of relying purely on embedding similarity.
**Cost:** Zero — pure dict mapping.
**Do first.** Baseline for everything else.

---

## Option 2 — Section-aware chunking with section labels

FDA labels have a consistent top-level structure:
1. Indications and Usage
2. Dosage and Administration
3. Dosage Forms and Strengths
4. Contraindications
5. Warnings and Precautions
6. Adverse Reactions
7. Drug Interactions
8. Use in Specific Populations
9. Clinical Pharmacology
10. Clinical Studies
11. References
12. How Supplied / Storage

Parse the PDF (with `pdfplumber` or `unstructured`) to detect section headings and tag each
chunk:

```python
{
    "section": "Warnings and Precautions",
    "subsection": "Immune-Mediated Adverse Reactions",
    "page_number": 14,
    "section_number": "5.1",
}
```

**Why it helps:**
- Direct section filtering: "What are the contraindications for Keytruda?" can pre-filter to
  `section == "Contraindications"` before vector search — massive precision boost.
- Avoids returning dosing info when the user asks about safety, or vice versa.
- Oncology labels (Keytruda, Opdivo) are enormous (100+ pages); section filtering is essential.

**Cost:** Medium — requires reliable heading detection. PDFs from DailyMed tend to be
structured but not always perfectly machine-readable. `unstructured` with its `partition_pdf`
handles most cases; fallback to regex on capitalized heading patterns.

---

## Option 3 — Drug class and therapeutic area tags (LLM-extracted, once per document)

Run a one-time extraction pass over each document (or use the indications text from the table)
to produce structured tags:

```python
{
    "drug_class": "PD-1/PD-L1 inhibitor",
    "therapeutic_area": ["oncology"],
    "mechanism_summary": "Blocks PD-1 receptor to restore anti-tumor T-cell activity",
    "route_of_administration": "intravenous",
    "molecule_type": "monoclonal antibody",     # vs. small molecule, vaccine, mRNA, etc.
    "has_black_box_warning": True,
    "rems_required": False,
}
```

**Why it helps:**
- Answers class-level questions: "Compare all PD-1 inhibitors" → filter on `drug_class`.
- Enables faceted search: "all IV biologics for oncology with a black box warning".
- `has_black_box_warning` is especially useful — those sections are clinically critical and
  users frequently ask about them.

**Cost:** Medium-high if using LLM. Low if derived from indications text via regex + a small
lookup table (drug class is often inferable from the mechanism-of-action section heading or
from the generic name suffix: `-mab` = monoclonal antibody, `-tinib` = kinase inhibitor, etc.).

Recommended approach: rule-based first, LLM-assisted for the hard cases.

---

## Option 4 — Contextual chunk headers (prepend-to-chunk technique)

Rather than just storing metadata in a separate field, prepend a short context header to each
chunk's text before embedding. This makes the metadata semantically searchable too:

```
[Keytruda (pembrolizumab) | PD-1 inhibitor | Merck | Section: Warnings and Precautions]
Immune-mediated adverse reactions, which may be severe or fatal, can occur with Keytruda...
```

**Why it helps:**
- The embedding captures the drug identity + section context, not just the raw clinical text.
- Prevents the well-known "lost in the middle" problem where short chunks lose their document
  context after chunking.
- Works with any vector store without needing metadata filter support.

**Cost:** Low — pure text manipulation. The main risk is inflating the chunk token count; keep
headers concise (< 20 tokens).

---

## Option 5 — Cross-drug relationship metadata

Several drugs in the corpus share active ingredients or drug classes. Encoding these
relationships helps for comparative queries.

**Same active ingredient (brand variants):**
- Ozempic / Wegovy / Rybelsus → all semaglutide (Novo Nordisk)
- Mounjaro / Zepbound → both tirzepatide (Eli Lilly)
- Prolia / Xgeva (if added) → both denosumab

**Same drug class clusters:**
- PD-1/PD-L1 checkpoint inhibitors: Keytruda, Opdivo, Tecentriq, Imfinzi
- GLP-1 receptor agonists: Ozempic, Wegovy, Rybelsus, Trulicity, Mounjaro (GIP+GLP-1)
- SGLT-2 inhibitors: Jardiance, Farxiga
- CDK4/6 inhibitors: Verzenio, Ibrance
- JAK inhibitors: Rinvoq
- IL-23 inhibitors: Skyrizi, Tremfya
- IL-17 inhibitors: Cosentyx
- IL-12/23 inhibitors: Stelara
- PARP inhibitors: Lynparza, Pomalyst (mechanism differs but myeloma overlap)
- Multiple myeloma agents: Darzalex, Revlimid, Pomalyst, Imbruvica

```python
{
    "same_active_ingredient_brands": ["Ozempic", "Wegovy", "Rybelsus"],
    "drug_class_peers": ["Ozempic", "Trulicity", "Mounjaro"],  # within GLP-1 class
}
```

**Why it helps:** Enables "compare semaglutide products" to pull from all three labels. Also
lets you build a class-level summary node in a hierarchical index.
**Cost:** Low — this mapping can be hand-authored from `top_50_drugs.md` in ~30 minutes.

---

## Option 6 — Query-type affinity tags

Tag sections with the *types of clinical questions* they answer. This is a light ontology:

| Section | Query affinity tags |
|---|---|
| Indications and Usage | `["eligibility", "indication", "approved for", "can I use"]` |
| Dosage and Administration | `["dosing", "how much", "how often", "titration", "administration"]` |
| Contraindications | `["contraindication", "who should not", "avoid in"]` |
| Warnings and Precautions | `["safety", "risk", "black box", "monitor", "serious adverse"]` |
| Adverse Reactions | `["side effects", "adverse events", "common reactions"]` |
| Drug Interactions | `["interaction", "co-administration", "avoid with", "CYP"]` |
| Use in Specific Populations | `["pregnancy", "pediatric", "renal impairment", "hepatic", "elderly"]` |
| Clinical Pharmacology | `["mechanism", "pharmacokinetics", "half-life", "Cmax"]` |
| Clinical Studies | `["efficacy", "trial", "study", "response rate", "OS", "PFS"]` |

Store as a list field. At query time, classify the incoming query into one of these tags and
add it as a metadata pre-filter.

**Why it helps:** Boosts precision significantly for specific query types. A dosing question
should almost never retrieve a pharmacokinetics chunk.
**Cost:** Low — rule-based mapping from section name, already defined by the SPL structure.

---

## Option 7 — Indication-specific sub-tagging for multi-indication drugs

Several drugs have approval for many separate indications (Keytruda has 40+, Dupixent has 6+).
Each indication has its own dosing, patient population, and study data. Chunking at the
document level loses this; we should tag chunks with which specific indication they cover.

```python
{
    "indication_specific": "Non-small cell lung cancer (NSCLC), first-line, PD-L1 ≥ 50%",
    "indication_code": "NSCLC_1L_high_PDL1",   # structured code if building a more formal schema
}
```

**Why it helps:** Prevents Keytruda's melanoma dosing from being returned for an NSCLC query.
Critical for drugs with indication-specific dosing regimens.
**Cost:** High — requires sub-section parsing and likely LLM assistance to segment and label
indication-specific content within sections. Best tackled after Options 1–3 are solid.

---

## Summary and Recommended Implementation Order

| Priority | Option | Effort | Impact |
|---|---|---|---|
| 1 | Static metadata from `top_50_drugs.md` | Low | Medium |
| 2 | Section-aware chunking + labels | Medium | High |
| 3 | Contextual chunk headers | Low | Medium-High |
| 4 | Drug class / therapeutic area tags | Medium | Medium-High |
| 5 | Cross-drug relationship metadata | Low | Medium |
| 6 | Query-type affinity tags | Low | High (if query classifier built) |
| 7 | Indication-specific sub-tagging | High | High for multi-indication drugs |

**Start with 1 + 2 + 3** — these are low-to-medium effort and unlock the largest gains.
Options 5 and 6 are cheap enough to add alongside the initial build.
Option 7 is the hardest and matters most for Keytruda, Opdivo, Dupixent, Humira — save for v2.

---

## Tooling Notes

- **PDF parsing:** `pdfplumber` (reliable for structured PDFs), `unstructured` (handles layout
  better for complex tables). DailyMed PDFs are generally clean.
- **Section detection:** Regex on ALL-CAPS or numbered headings; cross-reference against known
  SPL section list as a whitelist.
- **Vector store:** Metadata filtering requires a store that supports it — Chroma, Qdrant,
  Weaviate, LanceDB, or pgvector all work. Pinecone supports it too.
- **LLM extraction:** If using Claude, a single-pass extraction prompt over the first ~5 pages
  of each label can reliably get drug class, route, black box warning presence, and mechanism
  summary in one call per document (50 calls total — very cheap).
