"""
API Response Models
Pydantic 모델들로 응답 정의
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """작업 상태"""
    ACCEPTED = "accepted"       # 요청 접수됨
    QUEUED = "queued"          # 대기열에서 대기 중
    PROCESSING = "processing"   # 처리 중
    COMPLETED = "completed"     # 완료
    FAILED = "failed"          # 실패
    CANCELLED = "cancelled"     # 취소됨


class CallbackStatus(str, Enum):
    """콜백 전송 상태"""
    PENDING = "pending"        # 전송 대기
    SENT = "sent"             # 전송 완료
    FAILED = "failed"         # 전송 실패
    RETRYING = "retrying"     # 재시도 중


class ProcessingStep(BaseModel):
    """처리 단계 정보"""
    name: str = Field(..., description="단계 이름")
    status: Literal["pending", "processing", "completed", "failed"] = Field(..., description="단계 상태")
    started_at: Optional[datetime] = Field(default=None, description="시작 시간")
    completed_at: Optional[datetime] = Field(default=None, description="완료 시간")
    error: Optional[str] = Field(default=None, description="에러 메시지")


class TaskProgress(BaseModel):
    """작업 진행 상황"""
    current_step: Optional[str] = Field(default=None, description="현재 진행 단계")
    completed_steps: List[str] = Field(default_factory=list, description="완료된 단계들")
    total_steps: int = Field(default=5, description="전체 단계 수")
    percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="진행률 (0-100)")
    steps: List[ProcessingStep] = Field(default_factory=list, description="각 단계별 상세 정보")


class UnderwriteResult(BaseModel):
    """인수심사 결과"""
    status: Literal["success", "error"] = Field(..., description="결과 상태")
    
    # 핵심 가격책정 결과
    expected_loss: Optional[float] = Field(default=None, description="기댓값 손실 ($)")
    gross_premium: Optional[float] = Field(default=None, description="총 보험료 ($)")
    risk_level: Optional[str] = Field(default=None, description="리스크 레벨 (low/medium/high/very_high)")
    loss_ratio: Optional[float] = Field(default=None, description="손해율")
    coefficient_of_variation: Optional[float] = Field(default=None, description="변동계수")
    
    # 리스크 메트릭
    var_99: Optional[float] = Field(default=None, description="99% VaR ($)")
    tvar_99: Optional[float] = Field(default=None, description="99% TVaR ($)")
    simulation_years: Optional[int] = Field(default=None, description="시뮬레이션 연수")
    
    # 검증 및 품질
    validation_passed: bool = Field(default=False, description="검증 통과 여부")
    validation_checks: Optional[Dict[str, bool]] = Field(default=None, description="개별 검증 항목")
    alerts: Optional[List[str]] = Field(default=None, description="주의사항 목록")
    
    # 요약 정보
    event_type: Optional[str] = Field(default=None, description="이벤트 타입")
    recommendation: Optional[str] = Field(default=None, description="추천사항")
    executive_summary: Optional[str] = Field(default=None, description="경영진 요약")
    
    # 감사 추적 (옵션)
    audit_trail: Optional[Dict[str, Any]] = Field(default=None, description="감사 추적 정보")
    
    # 에러 정보 (실패 시)
    error: Optional[str] = Field(default=None, description="에러 메시지")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="상세 에러 정보")


class TaskResponse(BaseModel):
    """작업 응답 (즉시 반환)"""
    task_id: str = Field(..., description="작업 고유 ID")
    request_id: str = Field(..., description="클라이언트 요청 ID")
    status: TaskStatus = Field(..., description="작업 상태")
    estimated_duration_seconds: int = Field(..., description="예상 소요 시간 (초)")
    created_at: datetime = Field(..., description="생성 시간")
    started_at: Optional[datetime] = Field(default=None, description="시작 시간")
    status_url: str = Field(..., description="상태 조회 URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "underwriter_20240717_143022_abc123",
                "request_id": "client-uuid-123",
                "status": "accepted",
                "estimated_duration_seconds": 180,
                "created_at": "2024-07-17T14:30:22Z",
                "status_url": "/api/v1/tasks/underwriter_20240717_143022_abc123"
            }
        }


class TaskStatusResponse(BaseModel):
    """작업 상태 조회 응답"""
    task_id: str = Field(..., description="작업 고유 ID")
    request_id: str = Field(..., description="클라이언트 요청 ID")
    status: TaskStatus = Field(..., description="작업 상태")
    priority: str = Field(..., description="작업 우선순위")
    
    # 시간 정보
    created_at: datetime = Field(..., description="생성 시간")
    started_at: Optional[datetime] = Field(default=None, description="시작 시간")
    completed_at: Optional[datetime] = Field(default=None, description="완료 시간")
    processing_duration: Optional[float] = Field(default=None, description="처리 소요 시간 (초)")
    
    # 진행 상황
    progress: TaskProgress = Field(..., description="진행 상황")
    estimated_completion: Optional[datetime] = Field(default=None, description="예상 완료 시간")
    
    # 결과 및 에러
    result: Optional[UnderwriteResult] = Field(default=None, description="결과 (완료 시에만)")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    
    # 콜백 상태
    callback_status: CallbackStatus = Field(..., description="콜백 전송 상태")
    callback_attempts: int = Field(default=0, description="콜백 시도 횟수")
    last_callback_attempt: Optional[datetime] = Field(default=None, description="마지막 콜백 시도 시간")


class BatchTaskResponse(BaseModel):
    """배치 작업 응답"""
    batch_id: str = Field(..., description="배치 고유 ID")
    total_tasks: int = Field(..., description="전체 작업 수")
    tasks: List[TaskResponse] = Field(..., description="개별 작업 응답 목록")
    created_at: datetime = Field(..., description="생성 시간")


class HealthCheckResponse(BaseModel):
    """Health Check 응답"""
    status: Literal["healthy", "unhealthy"] = Field(..., description="서비스 상태")
    timestamp: datetime = Field(..., description="체크 시간")
    version: str = Field(..., description="API 버전")
    uptime_seconds: float = Field(..., description="가동 시간 (초)")
    
    # 의존성 상태
    dependencies: Dict[str, Literal["healthy", "unhealthy"]] = Field(..., description="의존성 서비스 상태")
    
    # 시스템 정보
    system_info: Optional[Dict[str, Any]] = Field(default=None, description="시스템 정보")


class ErrorResponse(BaseModel):
    """에러 응답"""
    error_code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[Dict[str, Any]] = Field(default=None, description="상세 정보")
    timestamp: datetime = Field(..., description="에러 발생 시간")
    request_id: Optional[str] = Field(default=None, description="요청 ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "VALIDATION_ERROR",
                "message": "User input contains forbidden characters",
                "details": {
                    "field": "user_input",
                    "invalid_chars": ["<", ">"]
                },
                "timestamp": "2024-07-17T14:30:22Z",
                "request_id": "client-uuid-123"
            }
        }