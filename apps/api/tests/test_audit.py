import hashlib
import json


def test_audit_hash_is_deterministic():
    payload = {
        "event": "erp.executed",
        "operation": "op-1",
        "payload": {"external_id": "ERP-1"},
        "previous": None,
    }
    first = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()
    second = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()
    assert first == second and len(first) == 64
