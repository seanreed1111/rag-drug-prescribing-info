"""Drug metadata registry parsed from top_50_drugs.md."""

import re
from pathlib import Path

# Map therapeutic areas from indications text
THERAPEUTIC_AREA_KEYWORDS = {
    "Oncology": ["cancer", "tumor", "carcinoma", "lymphoma", "myeloma", "leukemia", "melanoma", "sarcoma", "oncology"],
    "Immunology": ["psoriasis", "arthritis", "dermatitis", "crohn", "colitis", "lupus", "spondylitis", "autoimmune"],
    "Metabolic/Endocrine": ["diabetes", "obesity", "weight management", "glycemic"],
    "Cardiovascular": ["heart failure", "atrial fibrillation", "stroke", "anticoagulant", "thrombosis", "cardiomyopathy", "embolism"],
    "Neurology": ["multiple sclerosis", "sclerosis"],
    "Infectious Disease": ["hiv", "covid", "vaccine", "pneumococcal", "zoster", "shingles", "papillomavirus"],
    "Ophthalmology": ["macular degeneration", "macular edema", "retinopathy", "diabetic eye"],
    "Respiratory": ["asthma", "copd", "pulmonary fibrosis", "interstitial lung", "cystic fibrosis"],
    "Hematology": ["hemophilia", "myelodysplastic", "factor viii"],
    "Bone Health": ["osteoporosis", "fracture", "bone loss"],
    "Psychiatry": ["schizophrenia", "schizoaffective"],
}


def _classify_therapeutic_area(indications: str) -> str:
    """Classify a drug into a therapeutic area based on its indications text."""
    indications_lower = indications.lower()
    for area, keywords in THERAPEUTIC_AREA_KEYWORDS.items():
        if any(kw in indications_lower for kw in keywords):
            return area
    return "Other"


def _parse_top_50_drugs(md_path: Path) -> dict[str, dict]:
    """Parse top_50_drugs.md into a dict keyed by PDF filename stem.

    Returns:
        Dict mapping filename stem (e.g., "keytruda") to metadata dict with keys:
        brand_name, generic_name, manufacturer, rank, indications, therapeutic_area.
    """
    text = md_path.read_text(encoding="utf-8")
    registry: dict[str, dict] = {}

    # Match markdown table rows: | rank | brand | generic | manufacturer | sales | indications |
    row_pattern = re.compile(
        r"^\|\s*(\d+)\s*\|"       # rank
        r"\s*([^|]+?)\s*\|"       # brand name
        r"\s*([^|]+?)\s*\|"       # generic name
        r"\s*([^|]+?)\s*\|"       # manufacturer
        r"\s*[^|]+?\s*\|"         # sales (skip)
        r"\s*([^|]+?)\s*\|",      # indications
        re.MULTILINE,
    )

    for match in row_pattern.finditer(text):
        rank = int(match.group(1))
        brand_name = match.group(2).strip()
        generic_name = match.group(3).strip()
        manufacturer = match.group(4).strip()
        indications = match.group(5).strip()

        # Derive the PDF filename stem: lowercase, spaces to underscores, strip suffixes
        # Handle special cases like "Invega Sustenna/Trinza" or "Gardasil 9"
        stem = brand_name.split("/")[0].strip().lower().replace(" ", "_")
        # Remove trailing numbers for matching (e.g., "prevnar_20" -> "prevnar")
        stem_alt = re.sub(r"_?\d+$", "", stem)

        meta = {
            "brand_name": brand_name,
            "generic_name": generic_name,
            "manufacturer": manufacturer,
            "rank": rank,
            "indications": indications,
            "therapeutic_area": _classify_therapeutic_area(indications),
        }

        registry[stem] = meta
        if stem_alt != stem:
            registry[stem_alt] = meta

    return registry


# Module-level singleton
_REGISTRY: dict[str, dict] | None = None


def get_drug_metadata(pdf_filename: str, md_path: Path | None = None) -> dict:
    """Look up metadata for a drug by its PDF filename.

    Args:
        pdf_filename: e.g., "keytruda_prescribing_info.pdf"
        md_path: Path to top_50_drugs.md. Defaults to project root.

    Returns:
        Dict with brand_name, generic_name, manufacturer, rank, indications,
        therapeutic_area. Returns a minimal dict if drug not found.
    """
    global _REGISTRY
    if _REGISTRY is None:
        if md_path is None:
            md_path = Path(__file__).parent.parent / "top_50_drugs.md"
        _REGISTRY = _parse_top_50_drugs(md_path)

    # Extract stem from filename: "keytruda_prescribing_info.pdf" -> "keytruda"
    stem = pdf_filename.replace("_prescribing_info.pdf", "").replace("_prescribing_info.xml", "")

    if stem in _REGISTRY:
        return _REGISTRY[stem]

    # Fallback: return minimal metadata
    return {
        "brand_name": stem.replace("_", " ").title(),
        "generic_name": "unknown",
        "manufacturer": "unknown",
        "rank": 0,
        "indications": "unknown",
        "therapeutic_area": "Other",
    }
