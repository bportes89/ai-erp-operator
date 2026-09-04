from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models import OperationStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    organization: str | None = Field(default=None, max_length=160)


class OrgSettings(BaseModel):
    approval_threshold: float = Field(default=50000.0, gt=0)


class RecipeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=255)
    operation_type: str = Field(default="sales_order.create", max_length=60)
    field_aliases: dict = {}
    required_fields: list[str] = []
    approval_threshold: float | None = Field(default=None, gt=0)


class RecipeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    operation_type: str | None = None
    field_aliases: dict | None = None
    required_fields: list[str] | None = None
    approval_threshold: float | None = None
    active: bool | None = None


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None
    operation_type: str
    field_aliases: dict
    required_fields: list
    approval_threshold: float | None
    active: bool
    created_at: datetime


class ErpConnectorIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    base_url: str = Field(min_length=1, max_length=500)
    token: str | None = Field(default=None, max_length=255)
    auth_header: str = Field(default="Authorization", max_length=120)
    auth_scheme: str = Field(default="Bearer", max_length=80)
    create_path: str = Field(default="/orders", max_length=200)
    verify_path: str = Field(default="/orders/{external_id}", max_length=200)
    payload: str = Field(default="{}", max_length=4000)
    item_fields: str = Field(default="{}", max_length=500)
    external_id_path: str = Field(default="id", max_length=120)
    timeout: int = Field(default=10, ge=1, le=120)
    retries: int = Field(default=2, ge=0, le=5)
    active: bool = True


class ErpConnectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    base_url: str
    auth_header: str
    auth_scheme: str
    create_path: str
    verify_path: str
    payload: str
    item_fields: str
    external_id_path: str
    timeout: int
    retries: int
    active: bool
    token_last4: str | None = None
    created_at: datetime


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    description: str
    customer_code: str | None
    erp_code: str | None
    quantity: float
    unit_price: float
    total: float
    matched: bool


class OperationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    reference: str
    filename: str
    recipe_id: str | None = None
    supplier: str | None
    tax_id: str | None
    due_date: str | None
    cost_center: str | None
    total: float
    confidence: int
    status: OperationStatus
    issues: list = []
    created_at: datetime
    items: list[ItemOut] = []


class OperationPatch(BaseModel):
    reference: str | None = None
    supplier: str | None = None
    tax_id: str | None = None
    due_date: str | None = None
    cost_center: str | None = None
    total: float | None = None


class ItemPatch(BaseModel):
    description: str | None = None
    customer_code: str | None = None
    erp_code: str | None = None
    quantity: float | None = Field(default=None, gt=0)
    unit_price: float | None = Field(default=None, ge=0)


class MappingCreate(BaseModel):
    customer_code: str = Field(min_length=1, max_length=100)
    description: str
    erp_code: str = Field(min_length=1, max_length=100)


class MappingOut(MappingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    usage_count: int


class CustomerCreate(BaseModel):
    tax_id: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=255)
    erp_id: str | None = None
    default_cost_center: str | None = None
    payment_terms: str | None = None
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    erp_id: str | None = None
    default_cost_center: str | None = None
    payment_terms: str | None = None
    notes: str | None = None


class CustomerOut(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class ExecuteResult(BaseModel):
    operation_id: str
    external_id: str
    status: str
    executed_at: datetime


class DashboardOut(BaseModel):
    pending: int
    completed: int
    automation_rate: float
    minutes_saved: float
    processed_value: float


class WebhookCreate(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    secret: str | None = Field(default=None, max_length=128)
    events: list[str] = []


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    url: str
    events: list
    active: bool
    created_at: datetime


class WebhookDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event: str
    status: str
    attempts: int
    created_at: datetime


class DailyROI(BaseModel):
    date: str
    operations: int
    completed: int
    value: float


class ROIOut(BaseModel):
    total_operations: int
    completed: int
    pending: int
    automation_rate: float
    exception_rate: float
    avg_processing_seconds: float
    avg_time_to_erp_seconds: float
    processed_value: float
    hours_saved: float
    avg_confidence: int
    daily: list[DailyROI] = []
