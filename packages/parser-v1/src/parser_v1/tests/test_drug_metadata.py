"""Tests for the drug metadata registry."""

from pathlib import Path

from parser_v1.scripts.drug_metadata import (
    get_drug_metadata,
    _parse_top_50_drugs,
    _classify_therapeutic_area,
)

TOP_50_DRUGS_PATH = Path(__file__).parents[5] / "top_50_drugs.md"


def test_get_known_drug():
    meta = get_drug_metadata("keytruda_prescribing_info.pdf", md_path=TOP_50_DRUGS_PATH)
    assert meta["brand_name"] == "Keytruda"
    assert meta["rank"] == 1
    assert meta["therapeutic_area"] == "Oncology"
    assert meta["generic_name"] != "unknown"


def test_get_drug_metabolic():
    meta = get_drug_metadata("ozempic_prescribing_info.pdf", md_path=TOP_50_DRUGS_PATH)
    assert meta["therapeutic_area"] == "Metabolic/Endocrine"


def test_get_drug_cardiovascular():
    meta = get_drug_metadata("eliquis_prescribing_info.pdf", md_path=TOP_50_DRUGS_PATH)
    assert meta["therapeutic_area"] == "Cardiovascular"


def test_unknown_drug_returns_fallback():
    meta = get_drug_metadata(
        "nonexistent_prescribing_info.pdf", md_path=TOP_50_DRUGS_PATH
    )
    assert meta["generic_name"] == "unknown"
    assert meta["therapeutic_area"] == "Other"
    assert meta["rank"] == 0


def test_classify_therapeutic_area_oncology():
    assert (
        _classify_therapeutic_area("Treatment of melanoma and NSCLC cancer")
        == "Oncology"
    )


def test_classify_therapeutic_area_cardiovascular():
    assert (
        _classify_therapeutic_area("Prevention of stroke and atrial fibrillation")
        == "Cardiovascular"
    )


def test_classify_therapeutic_area_other():
    assert (
        _classify_therapeutic_area("Treatment of rare unclassified condition")
        == "Other"
    )


def test_parse_top_50_drugs_count():
    if not TOP_50_DRUGS_PATH.exists():
        return  # Skip if file not present
    registry = _parse_top_50_drugs(TOP_50_DRUGS_PATH)
    # Should have at least 50 entries (some drugs have multiple stems)
    unique_brands = {v["brand_name"] for v in registry.values()}
    assert len(unique_brands) >= 50, (
        f"Expected at least 50 unique drugs, got {len(unique_brands)}"
    )
