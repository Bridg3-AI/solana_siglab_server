"""
Notification Service
작업 완료 시 외부 모듈로 결과를 전송하는 서비스
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import httpx
from enum import Enum

from agents.core.logging import get_logger
from ..models import (
    CallbackConfig, CallbackType, CallbackStatus, 
    WebhookConfig, TaskStatusResponse, UnderwriteResult
)
from ..config import get_api_settings

settings = get_api_settings()
logger = get_logger("notification_service")


class NotificationMethod(str, Enum):
    WEBHOOK = "webhook"
    FILE_SYSTEM = "file_system"
    MESSAGE_QUEUE = "message_queue"


class RetryConfig:
    """재시도 설정"""
    def __init__(
        self,
        max_attempts: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 300.0,
        backoff_factor: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    def get_delay(self, attempt: int) -> float:
        """재시도 지연 시간 계산 (지수 백오프)"""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)


class WebhookClient:
    """Webhook 클라이언트"""
    
    def __init__(self, retry_config: RetryConfig = None):
        self.retry_config = retry_config or RetryConfig()
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
            headers={"User-Agent": "LLM-Lite-Underwriter-API/1.0"}
        )
    
    async def send_webhook(
        self, 
        webhook_config: WebhookConfig, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Webhook 전송"""
        
        url = str(webhook_config.url)
        headers = dict(webhook_config.headers) if webhook_config.headers else {}
        
        # Content-Type 기본값 설정
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        
        # 인증 헤더 추가
        if webhook_config.auth_header and webhook_config.auth_token:
            headers[webhook_config.auth_header] = webhook_config.auth_token
        
        logger.info("webhook_sending", 
                   url=url, 
                   payload_size=len(json.dumps(payload)),
                   headers_count=len(headers))
        
        # 재시도 로직 적용
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                response = await self.http_client.post(
                    url=url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                result = {
                    "success": response.is_success,
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers),
                    "response_body": None,
                    "attempt": attempt + 1,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 응답 바디 처리 (선택사항)
                try:
                    if response.headers.get("content-type", "").startswith("application/json"):
                        result["response_body"] = response.json()
                    else:
                        result["response_body"] = response.text[:1000]  # 최대 1KB만 저장
                except Exception:
                    result["response_body"] = "<unable to parse response>"
                
                if response.is_success:
                    logger.info("webhook_sent_successfully", 
                               url=url, 
                               status_code=response.status_code,
                               attempt=attempt + 1)
                    return result
                else:
                    logger.warning("webhook_failed", 
                                  url=url,
                                  status_code=response.status_code,
                                  attempt=attempt + 1,
                                  response_body=result.get("response_body", ""))
                    
                    # 4xx 에러는 재시도하지 않음
                    if 400 <= response.status_code < 500:
                        result["error"] = f"Client error {response.status_code} - not retrying"
                        return result
                    
                    # 5xx 에러는 재시도
                    last_exception = Exception(f"HTTP {response.status_code}")
                
            except Exception as e:
                logger.error("webhook_request_error", 
                           url=url,
                           attempt=attempt + 1,
                           error=str(e))
                last_exception = e
            
            # 마지막 시도가 아니면 대기
            if attempt < self.retry_config.max_attempts - 1:
                delay = self.retry_config.get_delay(attempt)
                logger.info("webhook_retry_delay", 
                           url=url,
                           attempt=attempt + 1,
                           delay_seconds=delay)
                await asyncio.sleep(delay)
        
        # 모든 재시도 실패
        return {
            "success": False,
            "error": str(last_exception),
            "total_attempts": self.retry_config.max_attempts,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def close(self):
        """HTTP 클라이언트 종료"""
        await self.http_client.aclose()


class FileSystemClient:
    """파일 시스템 클라이언트"""
    
    def __init__(self, base_directory: str = None):
        self.base_directory = Path(base_directory or settings.file_output_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
    
    async def write_result_file(
        self, 
        task_id: str, 
        result: Dict[str, Any],
        format: str = "json"
    ) -> Dict[str, Any]:
        """결과를 파일로 저장"""
        
        try:
            # 파일 경로 생성
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{task_id}_{timestamp}.{format}"
            file_path = self.base_directory / filename
            
            logger.info("writing_result_file", 
                       task_id=task_id,
                       file_path=str(file_path),
                       format=format)
            
            if format == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            else:
                # 다른 형식 지원 확장 가능
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(result))
            
            return {
                "success": True,
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("file_write_error", 
                        task_id=task_id,
                        error=str(e))
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class NotificationService:
    """알림 서비스"""
    
    def __init__(self):
        self.webhook_client = WebhookClient()
        self.file_client = FileSystemClient()
        logger.info("notification_service_initialized")
    
    async def send_task_completion_notification(
        self, 
        task_id: str,
        task_status: TaskStatusResponse,
        callback_config: CallbackConfig
    ) -> Dict[str, Any]:
        """작업 완료 알림 전송"""
        
        logger.info("sending_task_completion_notification", 
                   task_id=task_id,
                   callback_type=callback_config.type.value)
        
        # 알림 페이로드 생성
        payload = await self._create_notification_payload(task_status)
        
        notification_result = None
        
        try:
            if callback_config.type == CallbackType.WEBHOOK:
                if callback_config.webhook:
                    notification_result = await self.webhook_client.send_webhook(
                        callback_config.webhook, 
                        payload
                    )
                else:
                    notification_result = {
                        "success": False,
                        "error": "Webhook configuration is missing"
                    }
            
            elif callback_config.type == CallbackType.FILE_SYSTEM:
                notification_result = await self.file_client.write_result_file(
                    task_id, 
                    payload
                )
            
            elif callback_config.type == CallbackType.MESSAGE_QUEUE:
                # TODO: 메시지 큐 구현
                notification_result = {
                    "success": False,
                    "error": "Message queue notification not implemented yet"
                }
            
            else:
                notification_result = {
                    "success": False,
                    "error": f"Unsupported callback type: {callback_config.type}"
                }
            
            logger.info("notification_sent", 
                       task_id=task_id,
                       success=notification_result.get("success", False),
                       callback_type=callback_config.type.value)
            
            return notification_result
            
        except Exception as e:
            logger.error("notification_send_error", 
                        task_id=task_id,
                        callback_type=callback_config.type.value,
                        error=str(e))
            
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _create_notification_payload(self, task_status: TaskStatusResponse) -> Dict[str, Any]:
        """알림 페이로드 생성"""
        
        payload = {
            "task_id": task_status.task_id,
            "request_id": task_status.request_id,
            "status": task_status.status.value,
            "completed_at": task_status.completed_at.isoformat() if task_status.completed_at else None,
            "processing_duration": task_status.processing_duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 성공한 경우 결과 추가
        if task_status.status.value == "completed" and task_status.result:
            payload["result"] = task_status.result
            
            # UnderwriteResult인 경우 주요 정보 별도 추출
            if isinstance(task_status.result, dict):
                payload["summary"] = {
                    "expected_loss": task_status.result.get("expected_loss"),
                    "gross_premium": task_status.result.get("gross_premium"),
                    "risk_level": task_status.result.get("risk_level"),
                    "loss_ratio": task_status.result.get("loss_ratio")
                }
        
        # 실패한 경우 에러 정보 추가
        elif task_status.status.value == "failed" and task_status.error:
            payload["error"] = task_status.error
        
        # 진행률 정보 추가
        if task_status.progress:
            payload["progress"] = {
                "percentage": task_status.progress.percentage,
                "current_step": task_status.progress.current_step,
                "completed_steps": task_status.progress.completed_steps
            }
        
        return payload
    
    async def test_webhook_connection(self, webhook_config: WebhookConfig) -> Dict[str, Any]:
        """Webhook 연결 테스트"""
        
        test_payload = {
            "test": True,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "This is a test notification from LLM-Lite Underwriter API"
        }
        
        logger.info("testing_webhook_connection", url=str(webhook_config.url))
        
        result = await self.webhook_client.send_webhook(webhook_config, test_payload)
        
        return {
            "webhook_url": str(webhook_config.url),
            "test_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def close(self):
        """리소스 정리"""
        await self.webhook_client.close()
        logger.info("notification_service_closed")


# 전역 NotificationService 인스턴스
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """NotificationService 싱글톤 인스턴스 반환"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service