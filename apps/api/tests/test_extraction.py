from app.extraction import ExtractionResult, _extract_items, parse_number
from app.extraction_llm import _split_code_description


def test_split_code_description():
    code, desc = _split_code_description("CIM-1 Cimento CP-II 50kg")
    assert code == "CIM-1"
    assert desc == "Cimento CP-II 50kg"
    code, desc = _split_code_description("Areia Fina")
    assert code is None
    assert desc == "Areia Fina"


def test_parse_number_br_format():
    assert parse_number("R$ 1.234,56") == 1234.56
    assert parse_number("1234,56") == 1234.56
    assert parse_number("1,234.56") == 1234.56
    assert parse_number("1.234") == 1234.0
    assert parse_number("0") == 0.0


def test_extract_items_tabular():
    lines = [
        "Produto Qtd Valor Total",
        "ABC-120 Cimento Premium 30 49.90 1497.00",
        "XYZ-9 Areia Fina 10 80.00 800.00",
    ]
    items = _extract_items(lines)
    assert len(items) == 2
    assert items[0]["customer_code"] == "ABC-120"
    assert items[0]["quantity"] == 30.0
    assert items[0]["unit_price"] == 49.9
    assert items[0]["total"] == 1497.0


def test_extract_items_br_decimal():
    lines = ["CIMENTO 20 49,90 998,00"]
    items = _extract_items(lines)
    assert len(items) == 1
    assert items[0]["quantity"] == 20.0
    assert items[0]["unit_price"] == 49.9
    assert items[0]["total"] == 998.0


def test_extract_items_dedup():
    lines = ["PROD-A Descricao 5 10,00 50,00", "PROD-A Descricao 5 10,00 50,00"]
    assert len(_extract_items(lines)) == 1


def test_extract_result_contract():
    result = ExtractionResult(fields={"reference": "PC-1", "total": 100.0}, items=[], confidence=92)
    assert result.confidence == 92
    assert result.fields["reference"] == "PC-1"