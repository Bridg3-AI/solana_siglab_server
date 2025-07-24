"""
Webhook Models
외부 모듈로 전송할 데이터 모델
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

from .response import UnderwriteResult


class WebhookPayload(BaseModel):
    """Webhook 전송 페이로드"""
    
    # 기본 정보
    task_id: str = Field(..., description="작업 고유 ID")
    request_id: str = Field(..., description="클라이언트 요청 ID")
    status: str = Field(..., description="작업 완료 상태 (completed/failed)")
    
    # 시간 정보
    completed_at: datetime = Field(..., description="완료 시간")
    processing_duration: float = Field(..., description="처리 소요 시간 (초)")
    
    # 원본 요청 정보
    original_request: Dict[str, Any] = Field(..., description="원본 요청 데이터")
    
    # 결과 (성공 시)
    result: Optional[UnderwriteResult] = Field(default=None, description="인수심사 결과")
    
    # 에러 정보 (실패 시)
    error: Optional[str] = Field(default=None, description="에러 메시지")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="상세 에러 정보")
    
    # 메타데이터
    api_version: str = Field(default="v1", description="API 버전")
    webhook_version: str = Field(default="1.0", description="Webhook 스키마 버전")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "underwriter_20240717_143022_abc123",
                "request_id": "client-uuid-123",
                "status": "completed",
                "completed_at": "2024-07-17T14:33:22Z",
                "processing_duration": 178.5,
                "original_request": {
                    "user_input": "태풍 보험 상품을 설계해줘",
                    "options": {"simulation_years": 1000}
                },
                "result": {
                    "status": "success",
                    "expected_loss": 1250000,
                    "gross_premium": 1875000,
                    "risk_level": "medium",
                    "validation_passed": True
                },
                "api_version": "v1",
                "webhook_version": "1.0"
            }
        }


class WebhookDeliveryAttempt(BaseModel):
    """Webhook 전송 시도 기록"""
    
    attempt_number: int = Field(..., description="시도 번호 (1부터 시작)")
    timestamp: datetime = Field(..., description="시도 시간")
    url: str = Field(..., description="전송 대상 URL")
    
    # 요청 정보
    headers: Dict[str, str] = Field(..., description="전송 헤더")
    payload_size: int = Field(..., description="페이로드 크기 (bytes)")
    
    # 응답 정보
    status_code: Optional[int] = Field(default=None, description="HTTP 상태 코드")
    response_time_ms: Optional[float] = Field(default=None, description="응답 시간 (ms)")
    response_headers: Optional[Dict[str, str]] = Field(default=None, description="응답 헤더")
    response_body: Optional[str] = Field(default=None, max_length=1000, description="응답 본문 (1KB 제한)")
    
    # 결과
    success: bool = Field(..., description="전송 성공 여부")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    
    # 재시도 정보
    retry_after: Optional[int] = Field(default=None, description="재시도까지 대기 시간 (초)")


class WebhookDeliveryStatus(BaseModel):
    """Webhook 전송 상태"""
    
    task_id: str = Field(..., description="작업 ID")
    webhook_url: str = Field(..., description="Webhook URL")
    
    # 전송 상태
    status: str = Field(..., description="전송 상태 (pending/sent/failed/retrying)")
    total_attempts: int = Field(..., description="총 시도 횟수")
    max_attempts: int = Field(..., description="최대 시도 횟수")
    
    # 시간 정보
    first_attempt: Optional[datetime] = Field(default=None, description="첫 시도 시간")
    last_attempt: Optional[datetime] = Field(default=None, description="마지막 시도 시간")
    next_retry: Optional[datetime] = Field(default=None, description="다음 재시도 시간")
    
    # 시도 기록
    attempts: list[WebhookDeliveryAttempt] = Field(default_factory=list, description="전송 시도 기록")
    
    # 최종 결과
    final_success: Optional[bool] = Field(default=None, description="최종 성공 여부")
    final_error: Optional[str] = Field(default=None, description="최종 에러 메시지")