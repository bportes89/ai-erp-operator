import re
from dataclasses import dataclass
from io import BytesIO
from pypdf import PdfReader

@dataclass
class ExtractionResult:
    fields: dict
    items: list[dict]
    confidence: int


ALIASES = {
    "reference": ["referencia", "numero do pedido", "n. pedido", "numero da nf", "n. nf", "orçamento", "orcamento", "n. orçamento"],
    "supplier": ["fornecedor", "cliente", "razao social", "empresa", "cliente/fornecedor"],
    "tax_id": ["cnpj", "cpf/cnpj", "cnpj do cliente"],
    "due_date": ["vencimento", "data de entrega", "entrega", "data vencimento"],
    "cost_center": ["centro_custo", "centro de custo", "cc"],
    "total": ["total", "valor total", "total geral", "total do pedido"],
}


def _normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _value(lines: list[str], aliases: list[str]) -> str:
    for index, line in enumerate(lines):
        normalized = _normalize(line).lower().strip(" :")
        for alias in aliases:
            if normalized == alias:
                if index + 1 < len(lines):
                    return lines[index + 1].strip()
            if normalized.startswith(alias + ":"):
                return line.split(":", 1)[1].strip()
            if normalized.startswith(alias + " "):
                rest = line[len(alias):].strip()
                if ":" in rest:
                    rest = rest.split(":", 1)[1].strip()
                if re.search(r"\d", rest) and len(rest) < 40:
                    return rest
                if (
                    index + 1 < len(lines)
                    and len(rest) < 40
                    and parse_number(lines[index + 1]) is not None
                ):
                    return lines[index + 1].strip()
    return ""


def parse_number(raw: str) -> float | None:
    """Converte 'R$ 1.234,56' / '1234,56' / '1,234.56' / '1.234' em float."""
    candidates = re.findall(r"\d[\d.,]*", raw)
    text = (candidates[-1] if candidates else raw).replace("R$", "").replace(" ", "").replace("\xa0", "").strip()
    if not text:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", text):
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
    elif "." in text:
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def _extract_items(lines: list[str]) -> list[dict]:
    """Heurística de linhas de item: [CÓDIGO] descrição QTD [VL.UNIT] TOTAL."""
    code_re = re.compile(r"^[A-Z][A-Z0-9\-_/.]{1,24}$")
    header_re = re.compile(
        r"(qtd|quant|qtde|quantidade|qty|unit|vl|preco|preço|valor|total)", re.IGNORECASE
    )
    items: list[dict] = []
    in_table = False
    for line in lines:
        norm = _normalize(line)
        if header_re.search(norm) and len(norm) < 60:
            in_table = True
            continue
        if in_table and re.fullmatch(r"[-=_\s|*]+", norm):
            continue
        tokens = norm.split(" ")
        tail_end = len(tokens)
        while tail_end > 0 and parse_number(tokens[tail_end - 1]) is not None:
            tail_end -= 1
        tail = tokens[tail_end:]
        if len(tail) < 2:
            continue
        numbers = [parse_number(t) for t in tail]
        if any(n is None for n in numbers):
            continue
        total = numbers[-1]
        qty = numbers[-3] if len(numbers) >= 3 else numbers[-2]
        unit = numbers[-2] if len(numbers) >= 3 else None
        if unit is not None and abs(qty * unit - total) > max(0.01, total * 0.02):
            unit = None
        if unit is None:
            unit = round(total / qty, 2) if qty else 0.0
        head = tokens[:tail_end]
        code = None
        if head and len(head) > 1 and code_re.match(head[0]):
            code = head[0]
            desc = " ".join(head[1:])
        else:
            desc = " ".join(head)
        desc = desc.strip()
        if not desc:
            continue
        items.append(
            {
                "description": desc,
                "customer_code": code,
                "erp_code": None,
                "quantity": qty,
                "unit_price": round(unit, 2),
                "total": round(total, 2),
            }
        )
    dedup: list[dict] = []
    seen = set()
    for item in items:
        key = (item["customer_code"], item["description"], item["total"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
    return dedup


def extract_pdf(content: bytes) -> ExtractionResult:
    reader = PdfReader(BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields = {key: _value(lines, aliases) for key, aliases in ALIASES.items()}
    total = parse_number(fields["total"]) or 0.0
    fields["total"] = total
    cnpj = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", text)
    fields["tax_id"] = fields["tax_id"] or (cnpj.group() if cnpj else "")
    if fields["reference"] and not re.search(r"\d", fields["reference"]):
        fields["reference"] = ""
    items = _extract_items(lines)
    items_total = round(sum(i["total"] for i in items), 2)
    fields_pct = round(sum(bool(v) for v in fields.values()) / len(fields) * 100)
    items_bonus = 15 if items else 0
    confidence = min(99, fields_pct * 0.75 + items_bonus + (10 if items_total else 0))
    return ExtractionResult(
        fields=fields,
        items=items,
        confidence=round(confidence),
    )
