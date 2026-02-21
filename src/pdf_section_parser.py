"""Section-aware parser for FDA drug prescribing information PDFs."""

import re
from pathlib import Path

from pypdf import PdfReader
from llama_index.core import Document

# Standard FDA label section headers (numbered).
# Regex matches lines like "5 WARNINGS AND PRECAUTIONS" or "12.1 Mechanism of Action"
SECTION_HEADER_RE = re.compile(
    r"^(\d{1,2}(?:\.\d{1,2})?)\s+"  # section number (e.g., "5", "12.1")
    r"([A-Z][A-Z &,/\-]{2,}.*?)$",  # title in UPPER CASE (at least 3 chars)
    re.MULTILINE,
)

# Top-level section numbers (no dot)
TOP_LEVEL_RE = re.compile(r"^\d{1,2}$")


def extract_full_text(pdf_path: Path) -> str:
    """Extract all text from a PDF using pypdf."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _find_sections(text: str) -> list[tuple[str, str, int]]:
    """Find all section headers and their positions in the text.

    Returns list of (section_number, section_title, start_position).
    """
    sections = []
    for match in SECTION_HEADER_RE.finditer(text):
        num = match.group(1)
        title = match.group(2).strip()
        pos = match.start()
        sections.append((num, title, pos))
    return sections


def _deduplicate_sections(sections: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    """Remove duplicate section headers (TOC entries vs actual sections).

    The TOC at the beginning lists sections, then they appear again in the body.
    Keep the LAST occurrence of each section number (the actual content).
    """
    seen: dict[str, int] = {}
    for i, (num, title, pos) in enumerate(sections):
        seen[num] = i  # overwrite with later occurrence

    unique_indices = sorted(seen.values())
    return [sections[i] for i in unique_indices]


def parse_pdf_into_sections(
    pdf_path: Path,
    base_metadata: dict | None = None,
) -> list[Document]:
    """Parse a prescribing info PDF into section-level Documents.

    Each Document contains the text of one FDA label section, with metadata:
    - fda_section: e.g., "5 WARNINGS AND PRECAUTIONS"
    - fda_subsection: e.g., "5.1 Immune-Mediated Pneumonitis" (empty for top-level)
    - source_file: the PDF filename
    - Plus any keys from base_metadata

    Args:
        pdf_path: Path to the PDF file.
        base_metadata: Additional metadata to attach to every Document (drug info).

    Returns:
        List of Document objects, one per section/subsection.
    """
    if base_metadata is None:
        base_metadata = {}

    full_text = extract_full_text(pdf_path)
    sections = _find_sections(full_text)
    sections = _deduplicate_sections(sections)

    if not sections:
        # Fallback: return entire document as one chunk if no sections found
        doc = Document(
            text=full_text,
            metadata={
                **base_metadata,
                "source_file": pdf_path.name,
                "fda_section": "FULL PRESCRIBING INFORMATION",
                "fda_subsection": "",
            },
        )
        doc.excluded_embed_metadata_keys = ["source_file", "rank"]
        doc.excluded_llm_metadata_keys = ["rank"]
        return [doc]

    documents = []
    current_top_section = ""

    for i, (num, title, start) in enumerate(sections):
        # Get text from this section to the next
        end = sections[i + 1][2] if i + 1 < len(sections) else len(full_text)
        section_text = full_text[start:end].strip()

        # Skip very short sections (likely just headers with no content)
        if len(section_text) < 20:
            continue

        # Track top-level vs subsection
        if TOP_LEVEL_RE.match(num):
            current_top_section = f"{num} {title}"
            fda_section = current_top_section
            fda_subsection = ""
        else:
            fda_section = current_top_section
            fda_subsection = f"{num} {title}"

        metadata = {
            **base_metadata,
            "source_file": pdf_path.name,
            "fda_section": fda_section,
            "fda_subsection": fda_subsection,
        }

        doc = Document(text=section_text, metadata=metadata)
        doc.excluded_embed_metadata_keys = ["source_file", "rank"]
        doc.excluded_llm_metadata_keys = ["rank"]
        documents.append(doc)

    return documents
