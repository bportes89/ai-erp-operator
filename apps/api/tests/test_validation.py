from app.validation import is_valid_cnpj, validate_extraction
from app.extraction import ExtractionResult


def test_cnpj_valid():
    assert is_valid_cnpj("11.222.333/0001-81") is True


def test_cnpj_invalid():
    assert is_valid_cnpj("11.222.333/0001-00") is False


def test_cnpj_missing_returns_none():
    assert is_valid_cnpj("") is None


def test_validate_extraction_total_mismatch():
    result = ExtractionResult(
        fields={"reference": "PC-1", "total": 1000.0},
        items=[{"total": 500.0, "quantity": 1, "unit_price": 500.0, "description": "X"}],
        confidence=90,
    )
    issues = validate_extraction(result)
    assert any("diverge" in issue for issue in issues)


def test_validate_extraction_ok():
    result = ExtractionResult(
        fields={"reference": "PC-1", "total": 500.0},
        items=[{"total": 500.0, "quantity": 1, "unit_price": 500.0, "description": "X"}],
        confidence=90,
    )
    assert validate_extraction(result) == []