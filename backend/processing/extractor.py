from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docx import Document
from pypdf import PdfReader


def extract_text(file_path: str | Path) -> dict[str, Any]:
    """Extract readable text from a supported document file."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    try:
        if suffix == ".txt":
            text = path.read_text(encoding="utf-8")
            pages = 1
        elif suffix == ".docx":
            document = Document(path)
            paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
            text = "\n".join(paragraphs)
            pages = 1
        elif suffix == ".pdf":
            reader = PdfReader(str(path))
            text_parts = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(part.strip() for part in text_parts if part and part.strip())
            pages = len(reader.pages)
        else:
            return {"success": False, "error": "Unsupported file type"}

        return {
            "text": text,
            "pages": pages,
            "characters": len(text),
            "success": True,
        }
    except Exception as exc:  # pragma: no cover - defensive path
        return {"success": False, "error": str(exc)}


def save_extraction_result(file_path: str | Path, payload: dict[str, Any], output_dir: str | Path | None = None) -> Path:
    """Persist the extraction result as a JSON file."""
    path = Path(file_path)
    destination_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parents[1] / "data"
    destination_dir.mkdir(parents=True, exist_ok=True)

    output_path = destination_dir / f"{path.stem}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    return output_path
