from app.models import Operation, OperationStatus
from app.rules import DEFAULT_APPROVAL_THRESHOLD, approval_threshold, needs_approval


def _op(total: float) -> Operation:
    return Operation(
        id="op-1",
        organization_id="org-1",
        reference="PC-1",
        filename="p.pdf",
        total=total,
        confidence=90,
        status=OperationStatus.READY,
    )


def test_approval_threshold_default_and_custom():
    assert approval_threshold({}) == DEFAULT_APPROVAL_THRESHOLD
    assert approval_threshold({"approval_threshold": 10000}) == 10000.0
    assert approval_threshold({"approval_threshold": "abc"}) == DEFAULT_APPROVAL_THRESHOLD


def test_needs_approval_above_threshold():
    assert needs_approval(_op(60000.0), {"approval_threshold": 50000}) is True


def test_needs_approval_below_threshold():
    assert needs_approval(_op(1000.0), {"approval_threshold": 50000}) is False


def test_needs_approval_default_threshold():
    assert needs_approval(_op(60000.0), {}) is True
    assert needs_approval(_op(49999.0), {}) is False