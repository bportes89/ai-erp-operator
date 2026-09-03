from app.models import Operation

DEFAULT_APPROVAL_THRESHOLD = 50000.0


def approval_threshold(settings: dict) -> float:
    raw = settings.get("approval_threshold") if settings else None
    try:
        value = float(raw)
        return value if value > 0 else DEFAULT_APPROVAL_THRESHOLD
    except (TypeError, ValueError):
        return DEFAULT_APPROVAL_THRESHOLD


def needs_approval(operation: Operation, settings: dict, threshold_override: float | None = None) -> bool:
    """Pedido acima do limite da organização exige aprovação de um administrador."""
    threshold = threshold_override if threshold_override is not None else approval_threshold(settings)
    return float(operation.total) >= threshold