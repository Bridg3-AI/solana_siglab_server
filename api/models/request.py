"""
API Request Models
Pydantic 모델들로 입력 요청 정의
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum
import uuid


class CallbackType(str, Enum):
    """콜백 타입 열거형"""
    WEBHOOK = "webhook"
    FILE_SYSTEM = "filesystem" 
    MESSAGE_QUEUE = "message_queue"
    NONE = "none"


class UnderwriteOptions(BaseModel):
    """인수심사 옵션"""
    simulation_years: int = Field(default=1000, ge=100, le=10000, description="Monte Carlo 시뮬레이션 연수")
    debug_mode: bool = Field(default=False, description="디버그 모드 활성화")
    market_risk_premium: float = Field(default=0.15, ge=0.0, le=1.0, description="시장 리스크 프리미엄")
    enable_audit_trail: bool = Field(default=True, description="감사 추적 활성화")
    enable_tail_scenarios: bool = Field(default=True, description="Tail 시나리오 포함")


class WebhookConfig(BaseModel):
    """Webhook 설정"""
    url: HttpUrl = Field(..., description="결과를 받을 Webhook URL")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="추가 HTTP 헤더")
    retry_count: int = Field(default=3, ge=0, le=10, description="재시도 횟수")
    timeout_seconds: int = Field(default=30, ge=5, le=300, description="타임아웃 (초)")


class FileSystemConfig(BaseModel):
    """파일 시스템 출력 설정"""
    output_directory: str = Field(..., description="결과 파일 저장 디렉터리")
    filename_pattern: str = Field(default="{task_id}.json", description="파일명 패턴")
    include_timestamp: bool = Field(default=True, description="타임스탬프 포함")


class CallbackConfig(BaseModel):
    """콜백 설정"""
    type: CallbackType = Field(default=CallbackType.WEBHOOK, description="콜백 타입")
    webhook: Optional[WebhookConfig] = Field(default=None, description="Webhook 설정")
    filesystem: Optional[FileSystemConfig] = Field(default=None, description="파일시스템 설정")
    
    @validator('webhook')
    def validate_webhook_required(cls, v, values):
        if values.get('type') == CallbackType.WEBHOOK and v is None:
            raise ValueError('Webhook configuration is required when type is "webhook"')
        return v
    
    @validator('filesystem')
    def validate_filesystem_required(cls, v, values):
        if values.get('type') == CallbackType.FILE_SYSTEM and v is None:
            raise ValueError('Filesystem configuration is required when type is "filesystem"')
        return v


class UnderwriteRequest(BaseModel):
    """인수심사 요청"""
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="클라이언트 요청 ID")
    user_input: str = Field(..., min_length=5, max_length=1000, description="자연어 보험상품 요청")
    options: UnderwriteOptions = Field(default_factory=UnderwriteOptions, description="인수심사 옵션")
    callback: CallbackConfig = Field(default_factory=CallbackConfig, description="결과 전송 설정")
    priority: Literal["low", "normal", "high"] = Field(default="normal", description="작업 우선순위")
    
    @validator('user_input')
    def validate_user_input(cls, v):
        # 기본 보안 검증
        forbidden_chars = ['<', '>', '&', '"', "'"]
        if any(char in v for char in forbidden_chars):
            raise ValueError('User input contains forbidden characters')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "client-uuid-123",
                "user_input": "태풍 보험 상품을 설계해줘",
                "options": {
                    "simulation_years": 1000,
                    "debug_mode": False,
                    "market_risk_premium": 0.15,
                    "enable_audit_trail": True
                },
                "callback": {
                    "type": "webhook",
                    "webhook": {
                        "url": "https://client.example.com/underwrite-results",
                        "headers": {
                            "Authorization": "Bearer client-token"
                        },
                        "retry_count": 3
                    }
                },
                "priority": "normal"
            }
        }


class BatchUnderwriteRequest(BaseModel):
    """배치 인수심사 요청"""
    requests: list[UnderwriteRequest] = Field(..., min_items=1, max_items=10, description="배치 요청 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "requests": [
                    {
                        "request_id": "batch-1",
                        "user_input": "태풍 보험 상품을 설계해줘"
                    },
                    {
                        "request_id": "batch-2", 
                        "user_input": "지진 위험 보험 상품"
                    }
                ]
            }
        }