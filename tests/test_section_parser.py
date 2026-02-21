"""Tests for the section-aware PDF parser."""

from pathlib import Path

from src.pdf_section_parser import (
    parse_pdf_into_sections,
    _find_sections,
    _deduplicate_sections,
)

PRESCRIBING_INFO_DIR = Path(__file__).parent.parent / "prescribing_info"


def test_find_sections_basic():
    text = """HIGHLIGHTS OF PRESCRIBING INFORMATION

1 INDICATIONS AND USAGE
This drug is used for treating condition X.

2 DOSAGE AND ADMINISTRATION
Take 10mg daily.

2.1 RECOMMENDED DOSAGE
The recommended dose is 10mg.

5 WARNINGS AND PRECAUTIONS
Be careful.

5.1 HEPATOTOXICITY
May cause liver damage.
"""
    sections = _find_sections(text)
    nums = [s[0] for s in sections]
    assert "1" in nums
    assert "2" in nums
    assert "2.1" in nums
    assert "5" in nums
    assert "5.1" in nums


def test_deduplicate_sections():
    # Simulate TOC + body duplication
    sections = [
        ("1", "INDICATIONS AND USAGE", 10),  # TOC entry
        ("2", "DOSAGE AND ADMINISTRATION", 50),  # TOC entry
        ("1", "INDICATIONS AND USAGE", 200),  # Body entry
        ("2", "DOSAGE AND ADMINISTRATION", 500),  # Body entry
    ]
    deduped = _deduplicate_sections(sections)
    assert len(deduped) == 2
    assert deduped[0][2] == 200  # Kept the body entry
    assert deduped[1][2] == 500


def test_parse_real_pdf_eliquis():
    """Integration test with a real PDF."""
    pdf_path = PRESCRIBING_INFO_DIR / "eliquis_prescribing_info.pdf"
    if not pdf_path.exists():
        return  # Skip if PDFs not downloaded

    docs = parse_pdf_into_sections(pdf_path, base_metadata={"brand_name": "Eliquis"})

    assert len(docs) > 5, f"Expected at least 5 sections, got {len(docs)}"

    # Check metadata is present on all documents
    for doc in docs:
        assert "fda_section" in doc.metadata
        assert "source_file" in doc.metadata
        assert doc.metadata["source_file"] == "eliquis_prescribing_info.pdf"
        assert doc.metadata["brand_name"] == "Eliquis"

    # Check that we found key sections
    section_names = [doc.metadata["fda_section"] for doc in docs]
    assert any("INDICATIONS" in s for s in section_names), (
        f"No INDICATIONS section found in {section_names}"
    )
    assert any("WARNINGS" in s for s in section_names), (
        f"No WARNINGS section found in {section_names}"
    )
    assert any("ADVERSE" in s for s in section_names), (
        f"No ADVERSE section found in {section_names}"
    )


def test_parse_real_pdf_keytruda():
    """Integration test with Keytruda (largest PDF, 237 pages)."""
    pdf_path = PRESCRIBING_INFO_DIR / "keytruda_prescribing_info.pdf"
    if not pdf_path.exists():
        return

    docs = parse_pdf_into_sections(pdf_path)
    assert len(docs) > 10, (
        f"Expected at least 10 sections for Keytruda, got {len(docs)}"
    )

    # Subsections should have parent section info
    subsection_docs = [d for d in docs if d.metadata["fda_subsection"]]
    assert len(subsection_docs) > 0, "Expected some subsection documents"
