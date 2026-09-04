from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "development-only-secret"
    database_url: str = "sqlite+aiosqlite:///./operator.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "operator"
    storage_secret_key: str = "operator-secret"
    storage_bucket: str = "documents"
    storage_enabled: bool = True
    erp_mode: str = "demo"
    max_upload_mb: int = 10
    rate_limit_enabled: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    extraction_inline: bool = False
    erp_http_base_url: str = ""
    erp_http_token: str = ""
    erp_http_auth_header: str = "Authorization"
    erp_http_auth_scheme: str = "Bearer"
    erp_http_create_path: str = "/orders"
    erp_http_verify_path: str = "/orders/{external_id}"
    erp_http_payload: str = '{"reference":{reference},"supplier":{supplier},"tax_id":{tax_id},"due_date":{due_date},"cost_center":{cost_center},"total":{total},"idempotency_key":{idempotency_key},"items":{items}}'
    erp_http_item_fields: str = "{}"
    erp_http_external_id_path: str = "id"
    erp_http_timeout: int = 10
    erp_http_retries: int = 2
    llm_provider: str = "none"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
