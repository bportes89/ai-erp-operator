from app.export import operation_to_csv, operation_to_xml
from app.models import Operation, OperationItem, OperationStatus


def _op():
    return Operation(
        id="op-1",
        organization_id="org-1",
        reference="PC-100",
        filename="p.pdf",
        supplier="ACME",
        tax_id="11.222.333/0001-81",
        cost_center="FILIAL-MG",
        total=1497.0,
        confidence=90,
        status=OperationStatus.READY,
        items=[
            OperationItem(
                id="i-1",
                operation_id="op-1",
                description="Cimento",
                customer_code="CIM-1",
                erp_code="CIM-CP2",
                quantity=30,
                unit_price=49.9,
                total=1497.0,
                matched=True,
            )
        ],
    )


def test_csv_contains_header_and_item():
    csv_text = operation_to_csv(_op())
    assert "referencia" in csv_text
    assert "PC-100" in csv_text
    assert "CIM-CP2" in csv_text


def test_xml_contains_canonical_fields():
    xml_text = operation_to_xml(_op())
    assert "sales_order.create" in xml_text
    assert "PC-100" in xml_text
    assert "CIM-CP2" in xml_text
    assert "FILIAL-MG" in xml_text