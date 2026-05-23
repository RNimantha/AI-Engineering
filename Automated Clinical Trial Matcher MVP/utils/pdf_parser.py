"""
utils/pdf_parser.py
───────────────────
Reads a patient chart from a .txt or .pdf file and returns the raw text.

Design decision: We use PyMuPDF (fitz) for PDF parsing because it correctly
handles multi-column layouts and preserves reading order better than pypdf.
For plain text files we do a simple UTF-8 read with fallback to latin-1.

The output of this module is the raw_payload that feeds into Subagent 1
(Anonymizer). We deliberately do NOT strip whitespace or clean anything here
— the Anonymizer's LLM prompt is better at understanding messy clinical
formatting than regex pre-processing.
"""

from __future__ import annotations

import os
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class UnsupportedFileTypeError(Exception):
    """Raised when the input file is not a .pdf or .txt."""
    pass


def read_chart(file_path: str | Path) -> str:
    """
    Read a patient chart file and return its full text content.

    Args:
        file_path: Absolute or relative path to a .pdf or .txt file.

    Returns:
        Raw text content of the chart.

    Raises:
        FileNotFoundError:       If the file does not exist.
        UnsupportedFileTypeError: If the file extension is not .pdf or .txt.
        RuntimeError:            If parsing fails due to a corrupt file.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Chart file not found: {path}")

    suffix = path.suffix.lower()
    logger.info(f"Reading chart file: {path.name} ({suffix})")

    if suffix == ".txt":
        return _read_text_file(path)
    elif suffix == ".pdf":
        return _read_pdf_file(path)
    else:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix}'. Only .txt and .pdf are supported."
        )


def _read_text_file(path: Path) -> str:
    """Read a plain-text file with UTF-8 → latin-1 fallback."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning(f"UTF-8 decode failed for {path.name}, retrying with latin-1")
        text = path.read_text(encoding="latin-1")

    logger.info(f"Text file loaded — {len(text)} characters")
    return text


def _read_pdf_file(path: Path) -> str:
    """
    Extract text from a PDF using PyMuPDF.

    We use page.get_text("text") which returns plain text in reading order.
    Pages are joined with double newlines so the Anonymizer can reason about
    page breaks.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is not installed. Run: pip install PyMuPDF --break-system-packages"
        ) from exc

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF '{path.name}': {exc}") from exc

    pages_text: list[str] = []
    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text("text")
        if page_text.strip():
            pages_text.append(f"[Page {page_num}]\n{page_text}")

    doc.close()

    full_text = "\n\n".join(pages_text)
    logger.info(f"PDF loaded — {len(doc)} pages, {len(full_text)} characters")
    return full_text
