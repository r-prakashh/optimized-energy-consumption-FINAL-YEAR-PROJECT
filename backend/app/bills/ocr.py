"""Text extraction from uploaded electricity bills (PDF, photo, scan).

Pipeline, cheapest path first:

1. **Digital PDF** (e.g. a TNEB e-bill downloaded from the portal) — read the
   embedded text layer with `pypdf`. Exact, instant, no OCR error.
2. **Scanned PDF / photo / screenshot** — rasterise PDF pages with
   `pypdfium2`, then run `RapidOCR` (PaddleOCR's detection + recognition
   networks exported to ONNX). Pure pip install — no system Tesseract binary
   — so it runs unchanged on Render's free Python runtime.

Handwritten meter-reading notes are the hard case for any classical OCR
engine. When an Anthropic API key is configured, `app/bills/ai_extract.py`
adds a vision-model pass on top that reads handwriting far more reliably;
without a key the system still works on printed bills, and the UI always
lets the user correct the extracted values before analysis.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import numpy as np

MIN_TEXT_LAYER_CHARS = 40
PDF_RENDER_SCALE = 2.0  # ~144 DPI — enough for bill-sized print
MAX_PDF_PAGES = 4       # bills are 1-2 pages; caps cost on a stray long upload

IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp", "image/tiff"}
PDF_TYPES = {"application/pdf"}


class OcrUnavailableError(RuntimeError):
    """Raised when the OCR engine isn't installed in this environment."""


@dataclass
class OcrResult:
    text: str
    method: str                      # "pdf_text_layer" | "ocr"
    pages: int = 1
    confidence: float | None = None  # mean recognition confidence (OCR path only)
    lines: list[str] = field(default_factory=list)


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise OcrUnavailableError(
                "OCR engine not installed — run `pip install rapidocr-onnxruntime`."
            ) from exc
        _engine = RapidOCR()
    return _engine


def _ocr_image_array(image: np.ndarray) -> tuple[list[str], list[float]]:
    result, _ = _get_engine()(image)
    if not result:
        return [], []
    # Each item: [box_points, text, score]. Sort top-to-bottom, then
    # left-to-right so "Units consumed ... 245" stays on one logical line.
    items = sorted(result, key=lambda r: (round(min(p[1] for p in r[0]) / 12), min(p[0] for p in r[0])))
    lines: list[str] = []
    scores: list[float] = []
    current_row = None
    for box, text, score in items:
        row = round(min(p[1] for p in box) / 12)
        if current_row is not None and row == current_row and lines:
            lines[-1] = f"{lines[-1]}  {text}"
        else:
            lines.append(text)
        current_row = row
        scores.append(float(score))
    return lines, scores


def _image_bytes_to_array(data: bytes) -> np.ndarray:
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # phone photos carry rotation in EXIF
    img = img.convert("RGB")
    # Upscale small phone crops — recognition accuracy drops sharply below ~1000px.
    if max(img.size) < 1000:
        factor = 1000 / max(img.size)
        img = img.resize((int(img.width * factor), int(img.height * factor)))
    return np.array(img)


def _pdf_text_layer(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = reader.pages[:MAX_PDF_PAGES]
    text = "\n".join((p.extract_text() or "") for p in pages)
    return text, len(reader.pages)


def _pdf_ocr(data: bytes) -> tuple[list[str], list[float], int]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    lines: list[str] = []
    scores: list[float] = []
    n_pages = len(pdf)
    for i in range(min(n_pages, MAX_PDF_PAGES)):
        bitmap = pdf[i].render(scale=PDF_RENDER_SCALE)
        page_lines, page_scores = _ocr_image_array(np.array(bitmap.to_pil().convert("RGB")))
        lines.extend(page_lines)
        scores.extend(page_scores)
    return lines, scores, n_pages


def detect_kind(filename: str, content_type: str | None) -> str:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if ctype in PDF_TYPES or name.endswith(".pdf"):
        return "pdf"
    if ctype in IMAGE_TYPES or name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")):
        return "image"
    return "unknown"


def extract_text(data: bytes, filename: str, content_type: str | None) -> OcrResult:
    kind = detect_kind(filename, content_type)

    if kind == "pdf":
        text, n_pages = _pdf_text_layer(data)
        if len(text.strip()) >= MIN_TEXT_LAYER_CHARS:
            return OcrResult(text=text, method="pdf_text_layer", pages=n_pages, lines=text.splitlines())
        lines, scores, n_pages = _pdf_ocr(data)
        return OcrResult(
            text="\n".join(lines),
            method="ocr",
            pages=n_pages,
            confidence=round(float(np.mean(scores)), 3) if scores else None,
            lines=lines,
        )

    if kind == "image":
        lines, scores = _ocr_image_array(_image_bytes_to_array(data))
        return OcrResult(
            text="\n".join(lines),
            method="ocr",
            confidence=round(float(np.mean(scores)), 3) if scores else None,
            lines=lines,
        )

    raise ValueError("Unsupported file type — upload a PDF or an image (PNG/JPG/WEBP).")
