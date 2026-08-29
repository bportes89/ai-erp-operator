import pytest
from sqlalchemy import select

from app.matching import apply_matches, learn_mapping
from app.models import Operation, OperationItem, OperationStatus, ProductMapping


@pytest.mark.asyncio
async def test_apply_matches_uses_existing_mapping(session, org):
    session.add(
        ProductMapping(
            organization_id=org.id, customer_code="ABC-120", description="Cimento Premium", erp_code="CIM-CP2"
        )
    )
    op = Operation(
        organization_id=org.id,
        reference="PC-1",
        filename="p.pdf",
        total=1497.0,
        confidence=90,
        status=OperationStatus.READY,
        items=[OperationItem(description="Cimento Premium", customer_code="ABC-120", quantity=30, unit_price=49.9, total=1497.0)],
    )
    session.add(op)
    await session.commit()

    await apply_matches(session, op)
    await session.commit()

    assert op.items[0].erp_code == "CIM-CP2"
    assert op.items[0].matched is True
    mapping = await session.scalar(select(ProductMapping))
    assert mapping.usage_count == 1


@pytest.mark.asyncio
async def test_learn_mapping_from_correction(session, org):
    op = Operation(
        organization_id=org.id,
        reference="PC-2",
        filename="p.pdf",
        total=10.0,
        confidence=90,
        status=OperationStatus.READY,
        items=[OperationItem(description="Areia", customer_code="ARE-1", quantity=1, unit_price=10.0, total=10.0)],
    )
    session.add(op)
    await session.commit()

    item = op.items[0]
    item.erp_code = "ARE-FINA"
    mapping = await learn_mapping(session, item, org.id)
    await session.commit()

    assert mapping is not None
    assert mapping.customer_code == "ARE-1"
    assert mapping.erp_code == "ARE-FINA"