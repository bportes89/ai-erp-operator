import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OperationStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    REVIEW = "review"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("organization_id", "tax_id"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    tax_id: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(255))
    erp_id: Mapped[str | None] = mapped_column(String(100))
    default_cost_center: Mapped[str | None] = mapped_column(String(100))
    payment_terms: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="operator")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Operation(Base):
    __tablename__ = "operations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    reference: Mapped[str] = mapped_column(String(100), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(500))
    raw_content: Mapped[bytes | None] = mapped_column(LargeBinary)
    supplier: Mapped[str | None] = mapped_column(String(200))
    tax_id: Mapped[str | None] = mapped_column(String(30))
    due_date: Mapped[str | None] = mapped_column(String(30))
    cost_center: Mapped[str | None] = mapped_column(String(100))
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus), default=OperationStatus.RECEIVED, index=True
    )
    raw_extraction: Mapped[dict] = mapped_column(JSON, default=dict)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    items: Mapped[list["OperationItem"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class OperationItem(Base):
    __tablename__ = "operation_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    operation_id: Mapped[str] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(String(255))
    customer_code: Mapped[str | None] = mapped_column(String(100))
    erp_code: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    total: Mapped[float] = mapped_column(Numeric(12, 2))
    matched: Mapped[bool] = mapped_column(Boolean, default=False)


class ProductMapping(Base):
    __tablename__ = "product_mappings"
    __table_args__ = (UniqueConstraint("organization_id", "customer_code"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    customer_code: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255))
    erp_code: Mapped[str] = mapped_column(String(100))
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    operation_id: Mapped[str | None] = mapped_column(ForeignKey("operations.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    hash: Mapped[str] = mapped_column(String(64))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String, index=True)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Webhook(Base):
    __tablename__ = "webhooks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    secret: Mapped[str] = mapped_column(String(128))
    events: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_id: Mapped[str] = mapped_column(ForeignKey("webhooks.id"), index=True)
    event: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
