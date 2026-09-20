from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agentverse.core.errors import InvalidDocumentError


@dataclass(frozen=True, slots=True)
class OcrPage:
    page: int
    text: str
    confidence: float | None
    source_path: str


class TextExtractor(Protocol):
    def extract(self, path: Path) -> list[OcrPage]: ...


class OcrExtractor:
    """Local OCR adapter. Import heavy native dependencies only when invoked."""

    allowed_suffixes = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff"})

    def extract(self, path: Path) -> list[OcrPage]:
        resolved = path.resolve(strict=True)
        if resolved.suffix.lower() not in self.allowed_suffixes:
            raise InvalidDocumentError(f"unsupported OCR type: {resolved.suffix}")
        import pytesseract  # type: ignore[import-not-found]
        from PIL import Image  # type: ignore[import-not-found]

        with Image.open(resolved) as image:
            image.verify()
        with Image.open(resolved) as image:
            text = pytesseract.image_to_string(image, config="--psm 3")
        return [OcrPage(page=1, text=text.strip(), confidence=None, source_path=str(resolved))]
