import base64
import json
from io import BytesIO

import httpx
import pymupdf

from app.config import get_settings
from app.extraction import ExtractionResult, extract_pdf

SYSTEM_PROMPT = (
    "Você converte pedidos de compra B2B brasileiros (extraídos de PDF) em dados estruturados. "
    "Responda APENAS com JSON válido, sem comentários, neste formato:\n"
    '{"reference": string, "supplier": string, "tax_id": string (só dígitos ou formatado), '
    '"due_date": string, "cost_center": string, "total": number, '
    '"items": [{"description": string, "customer_code": string|null, '
    '"quantity": number, "unit_price": number, "total": number}]}\n'
    "Regras: campos ausentes devem ser string vazia ou null. Se a linha de item tiver código, "
    "coloque em customer_code. Valores monetários em números decimais. "
    "Não invente dados; use apenas o que está no documento."
)


def _call_llm(text: str) -> dict | None:
    s = get_settings()
    if s.llm_provider == "none" or not s.llm_api_key:
        return None
    url = (s.llm_base_url or "https://api.openai.com/v1/chat/completions").rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {s.llm_api_key}", "Content-Type": "application/json"}
    body = {
        "model": s.llm_model or "gpt-4o-mini",
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "DOCUMENTO:\n" + text[:14000]},
        ],
    }
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception:
        return None


def _split_code_description(description: str) -> tuple[str | None, str]:
    """Separa 'CIM-1 Cimento Premium' em código + descrição quando o modelo junta."""
    match = __import__("re").match(r"^([A-Z][A-Z0-9\-_/.]{1,24})\s+(.+)$", description.strip())
    if match:
        return match.group(1), match.group(2).strip()
    return None, description.strip()


def _sanitize(raw: dict) -> dict | None:
    """Valida e normaliza a saída do LLM contra o contrato; None se inutilizável."""
    try:
        items = []
        for it in raw.get("items") or []:
            if not isinstance(it, dict):
                continue
            qty = float(it.get("quantity") or 0)
            unit = float(it.get("unit_price") or 0)
            total = float(it.get("total") or 0)
            if qty <= 0:
                continue
            if not total:
                total = round(qty * unit, 2)
            description = str(it.get("description") or "").strip()
            code, description = _split_code_description(description)
            if not code and it.get("customer_code"):
                code = str(it["customer_code"]).strip()
            items.append(
                {
                    "description": description,
                    "customer_code": code,
                    "erp_code": None,
                    "quantity": qty,
                    "unit_price": round(unit, 2),
                    "total": round(total, 2),
                }
            )
        total = float(raw.get("total") or 0)
        fields = {
            "reference": (raw.get("reference") or "").strip(),
            "supplier": (raw.get("supplier") or "").strip(),
            "tax_id": (raw.get("tax_id") or "").strip(),
            "due_date": (raw.get("due_date") or "").strip(),
            "cost_center": (raw.get("cost_center") or "").strip(),
            "total": total,
        }
        return {"fields": fields, "items": items}
    except Exception:
        return None


def _merge(heuristic: ExtractionResult, llm: dict) -> ExtractionResult:
    fields = dict(heuristic.fields)
    for key in ("reference", "supplier", "tax_id", "due_date", "cost_center"):
        if llm["fields"].get(key):
            fields[key] = llm["fields"][key]
    if llm["fields"].get("total"):
        fields["total"] = llm["fields"]["total"]
    items = llm["items"] if llm["items"] else heuristic.items
    return ExtractionResult(fields=fields, items=items, confidence=heuristic.confidence)


def _render_pages(content: bytes, max_pages: int = 4, dpi: int = 180) -> list[bytes]:
    """Renderiza páginas do PDF como PNGs para OCR por visão."""
    images: list[bytes] = []
    doc = pymupdf.open(stream=content, filetype="pdf")
    try:
        for page in doc:
            if len(images) >= max_pages:
                break
            images.append(page.get_pixmap(dpi=dpi).tobytes("png"))
    finally:
        doc.close()
    return images


def _call_llm_vision(pages: list[bytes]) -> dict | None:
    s = get_settings()
    if s.llm_provider == "none" or not s.llm_api_key or not pages:
        return None
    url = (s.llm_base_url or "https://api.openai.com/v1/chat/completions").rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {s.llm_api_key}", "Content-Type": "application/json"}
    content_parts: list[dict] = [
        {
            "type": "text",
            "text": "Este é um documento escaneado. Extraia os dados conforme o formato solicitado.",
        }
    ]
    for image in pages:
        encoded = base64.b64encode(image).decode()
        content_parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded}"},
            }
        )
    body = {
        "model": s.llm_model or "gpt-4o-mini",
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content_parts},
        ],
    }
    try:
        with httpx.Client(timeout=90) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception:
        return None


def extract_text(content: bytes) -> ExtractionResult:
    """Pipeline de extração: texto (LLM) ou OCR por visão para PDFs escaneados."""
    heuristic = extract_pdf(content)
    s = get_settings()
    if s.llm_provider == "none" or not s.llm_api_key:
        return heuristic
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    scanned = len(text.strip()) < 40
    if not scanned:
        llm = _call_llm(text)
        if llm and _sanitize(llm):
            return _merge(heuristic, _sanitize(llm))
        return heuristic
    pages = _render_pages(content)
    llm = _call_llm_vision(pages)
    if llm and _sanitize(llm):
        result = _merge(heuristic, _sanitize(llm))
        result.fields["extraction_method"] = "ocr_vision"
        return result
    return heuristic
