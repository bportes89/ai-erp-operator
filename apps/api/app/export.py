import csv
import io
import xml.etree.ElementTree as ET

from app.models import Operation


def operation_to_csv(op: Operation) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["referencia", "cliente", "cnpj", "vencimento", "centro_custo", "total", "status"]
    )
    writer.writerow(
        [
            op.reference,
            op.supplier or "",
            op.tax_id or "",
            op.due_date or "",
            op.cost_center or "",
            f"{float(op.total):.2f}".replace(".", ","),
            op.status.value,
        ]
    )
    writer.writerow([])
    writer.writerow(["codigo_cliente", "descricao", "codigo_erp", "quantidade", "preco_unitario", "total"])
    for item in op.items:
        writer.writerow(
            [
                item.customer_code or "",
                item.description,
                item.erp_code or "",
                f"{float(item.quantity):g}",
                f"{float(item.unit_price):.2f}".replace(".", ","),
                f"{float(item.total):.2f}".replace(".", ","),
            ]
        )
    return buffer.getvalue()


def operation_to_xml(op: Operation) -> str:
    root = ET.Element(
        "operation", {"type": "sales_order.create", "version": "1.0"}
    )
    header = ET.SubElement(root, "header")
    ET.SubElement(header, "reference").text = op.reference
    ET.SubElement(header, "supplier").text = op.supplier or ""
    ET.SubElement(header, "tax_id").text = op.tax_id or ""
    ET.SubElement(header, "due_date").text = op.due_date or ""
    ET.SubElement(header, "cost_center").text = op.cost_center or ""
    ET.SubElement(header, "total").text = f"{float(op.total):.2f}"
    items = ET.SubElement(root, "items")
    for item in op.items:
        row = ET.SubElement(items, "item")
        ET.SubElement(row, "customer_code").text = item.customer_code or ""
        ET.SubElement(row, "description").text = item.description
        ET.SubElement(row, "erp_code").text = item.erp_code or ""
        ET.SubElement(row, "quantity").text = f"{float(item.quantity):g}"
        ET.SubElement(row, "unit_price").text = f"{float(item.unit_price):.2f}"
        ET.SubElement(row, "total").text = f"{float(item.total):.2f}"
    return ET.tostring(root, encoding="unicode")