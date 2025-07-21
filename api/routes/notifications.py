"""
Notifications Router
알림 시스템 관련 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from typing import Dict, Any

from agents.core.logging import get_logger
from ..models import WebhookConfig
from ..services.notification_service import get_notification_service
from ..config import get_api_settings

router = APIRouter()
logger = get_logger("notifications_router")
settings = get_api_settings()


@router.post("/test-webhook", status_code=status.HTTP_200_OK)
async def test_webhook_connection(webhook_config: WebhookConfig):
    """
    Webhook 연결 테스트
    
    제공된 webhook 설정으로 테스트 메시지를 전송하여 연결을 확인합니다.
    """
    
    logger.info("webhook_test_requested", url=str(webhook_config.url))
    
    try:
        notification_service = get_notification_service()
        test_result = await notification_service.test_webhook_connection(webhook_config)
        
        return {
            "message": "Webhook connection test completed",
            "test_result": test_result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("webhook_test_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test webhook connection: {str(e)}"
        )


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_notification_stats():
    """
    알림 시스템 통계
    
    알림 전송 관련 통계 정보를 반환합니다.
    """
    
    try:
        # TaskManager에서 콜백 관련 통계 수집
        from ..services.task_manager import get_task_manager
        
        task_manager = get_task_manager()
        all_tasks = await task_manager.list_tasks(limit=1000)
        
        # 콜백 상태별 통계
        callback_stats = {
            "total_tasks_with_callbacks": 0,
            "callback_success_count": 0,
            "callback_failed_count": 0,
            "callback_pending_count": 0,
            "callback_in_progress_count": 0,
            "avg_callback_attempts": 0.0
        }
        
        callback_tasks = [t for t in all_tasks if t.callback_config]
        callback_stats["total_tasks_with_callbacks"] = len(callback_tasks)
        
        if callback_tasks:
            from ..models import CallbackStatus
            
            callback_stats["callback_success_count"] = len([
                t for t in callback_tasks if t.callback_status == CallbackStatus.SUCCESS
            ])
            callback_stats["callback_failed_count"] = len([
                t for t in callback_tasks if t.callback_status == CallbackStatus.FAILED
            ])
            callback_stats["callback_pending_count"] = len([
                t for t in callback_tasks if t.callback_status == CallbackStatus.PENDING
            ])
            callback_stats["callback_in_progress_count"] = len([
                t for t in callback_tasks if t.callback_status == CallbackStatus.IN_PROGRESS
            ])
            
            # 평균 콜백 시도 횟수
            total_attempts = sum(t.callback_attempts for t in callback_tasks)
            callback_stats["avg_callback_attempts"] = total_attempts / len(callback_tasks)
        
        return {
            "timestamp": datetime.utcnow(),
            "notification_stats": callback_stats,
            "system_config": {
                "webhook_timeout_seconds": settings.webhook_timeout_seconds,
                "webhook_max_retries": settings.webhook_max_retries,
                "file_output_directory": settings.file_output_directory
            }
        }
        
    except Exception as e:
        logger.error("notification_stats_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification statistics"
        )