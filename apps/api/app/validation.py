import re
from app.extraction import ExtractionResult
from app.models import Operation


def is_valid_cnpj(value: str | None) -> bool | None:
    """None se ausente; True/False se presente."""
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    weights = ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    for index, weight in enumerate(weights):
        total = sum(int(a) * b for a, b in zip(digits[: len(weight)], weight))
        rest = total % 11
        check = 0 if rest < 2 else 11 - rest
        if check != int(digits[len(weight)]):
            return False
    return True


def validate_extraction(result: ExtractionResult) -> list[str]:
    issues: list[str] = []
    if not result.fields.get("reference"):
        issues.append("Referência do pedido não identificada")
    if is_valid_cnpj(result.fields.get("tax_id")) is False:
        issues.append("CNPJ inválido")
    items_total = round(sum(i["total"] for i in result.items), 2)
    header_total = result.fields.get("total") or 0.0
    if result.items and header_total and abs(items_total - header_total) > max(0.01, header_total * 0.02):
        issues.append(
            f"Soma dos itens (R$ {items_total:,.2f}) diverge do total (R$ {header_total:,.2f})"
        )
    return issues


def validate_operation(op: Operation) -> list[str]:
    issues: list[str] = []
    if op.items and abs(op.total - sum(i.total for i in op.items)) > max(0.01, op.total * 0.02):
        issues.append("Soma dos itens diverge do total do pedido")
    for item in op.items:
        if item.quantity <= 0:
            issues.append(f"Item {item.description or item.customer_code}: quantidade inválida")
        if item.unit_price < 0:
            issues.append(f"Item {item.description or item.customer_code}: preço inválido")
    return issues
