"""
API Configuration
환경 변수 및 설정 관리
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional


class APISettings(BaseSettings):
    """API 설정"""
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=False, env="API_DEBUG")
    
    # API 정보
    title: str = Field(default="LLM-Lite Underwriter API", env="API_TITLE")
    description: str = Field(default="파라메트릭 보험 자동 인수심사 API", env="API_DESCRIPTION")
    version: str = Field(default="1.0.0", env="API_VERSION")
    
    # CORS 설정
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], 
        env="API_CORS_ORIGINS"
    )
    cors_credentials: bool = Field(default=True, env="API_CORS_CREDENTIALS")
    cors_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], env="API_CORS_METHODS")
    
    # 보안 설정
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    valid_api_keys: List[str] = Field(default=[], env="API_VALID_KEYS")
    rate_limit_per_minute: int = Field(default=60, env="API_RATE_LIMIT")
    
    # 작업 관리 설정
    max_concurrent_tasks: int = Field(default=10, env="API_MAX_CONCURRENT_TASKS")
    task_timeout_seconds: int = Field(default=600, env="API_TASK_TIMEOUT")  # 10분
    task_cleanup_interval_hours: int = Field(default=24, env="API_TASK_CLEANUP_INTERVAL")
    
    # Redis 설정 (선택사항)
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Webhook 설정
    webhook_timeout_seconds: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    webhook_max_retries: int = Field(default=3, env="WEBHOOK_MAX_RETRIES")
    webhook_retry_backoff_multiplier: float = Field(default=2.0, env="WEBHOOK_BACKOFF_MULTIPLIER")
    webhook_max_payload_size: int = Field(default=10_000_000, env="WEBHOOK_MAX_PAYLOAD_SIZE")  # 10MB
    
    # 파일시스템 설정
    results_output_dir: str = Field(default="./api_results", env="API_RESULTS_DIR")
    log_output_dir: str = Field(default="./api_logs", env="API_LOGS_DIR")
    file_output_directory: str = Field(default="./api_notifications", env="API_NOTIFICATION_FILE_DIR")
    
    # 모니터링 설정
    enable_metrics: bool = Field(default=True, env="API_ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="API_METRICS_PORT")
    health_check_interval_seconds: int = Field(default=30, env="API_HEALTH_CHECK_INTERVAL")
    
    # UnderwriterAgent 기본 설정
    default_simulation_years: int = Field(default=1000, env="UNDERWRITER_DEFAULT_SIMULATION_YEARS")
    default_market_risk_premium: float = Field(default=0.15, env="UNDERWRITER_DEFAULT_MARKET_RISK_PREMIUM")
    enable_audit_trail_default: bool = Field(default=True, env="UNDERWRITER_ENABLE_AUDIT_TRAIL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    def get_cors_origins(self) -> List[str]:
        """CORS origins 파싱 (문자열로 전달된 경우 처리)"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return self.cors_origins
    
    def get_valid_api_keys(self) -> List[str]:
        """API keys 파싱 (문자열로 전달된 경우 처리)"""
        if isinstance(self.valid_api_keys, str):
            return [key.strip() for key in self.valid_api_keys.split(",") if key.strip()]
        return self.valid_api_keys
    
    def is_auth_enabled(self) -> bool:
        """인증 활성화 여부 확인"""
        return len(self.get_valid_api_keys()) > 0


class LoggingSettings(BaseSettings):
    """로깅 설정"""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    file_enabled: bool = Field(default=True, env="LOG_FILE_ENABLED")
    file_path: str = Field(default="./api_logs/api.log", env="LOG_FILE_PATH")
    file_max_size_mb: int = Field(default=100, env="LOG_FILE_MAX_SIZE_MB")
    file_backup_count: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")
    
    # Structured logging fields
    include_request_id: bool = Field(default=True, env="LOG_INCLUDE_REQUEST_ID")
    include_user_agent: bool = Field(default=True, env="LOG_INCLUDE_USER_AGENT")
    include_ip_address: bool = Field(default=True, env="LOG_INCLUDE_IP")
    
    class Config:
        env_file = ".env"


# 전역 설정 인스턴스
api_settings = APISettings()
logging_settings = LoggingSettings()


def get_api_settings() -> APISettings:
    """API 설정 반환"""
    return api_settings


def get_logging_settings() -> LoggingSettings:
    """로깅 설정 반환"""
    return logging_settings