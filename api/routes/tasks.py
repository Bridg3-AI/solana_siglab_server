"""
Tasks Router
작업 상태 조회 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, status, Path, Query
from datetime import datetime
from typing import Optional, List

from agents.core.logging import get_logger
from ..models import TaskStatusResponse, TaskStatus, UnderwriteResult
from ..services.task_manager import get_task_manager, TaskInfo
from ..config import get_api_settings

router = APIRouter()
logger = get_logger("tasks_router")
settings = get_api_settings()


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, status_code=status.HTTP_200_OK)
async def get_task_status(
    task_id: str = Path(..., description="작업 고유 ID", min_length=10, max_length=100)
):
    """
    작업 상태 조회
    
    task_id에 해당하는 작업의 상태, 진행률, 결과 등을 반환합니다.
    """
    
    logger.info("task_status_requested", task_id=task_id)
    
    try:
        task_manager = get_task_manager()
        task_info = await task_manager.get_task_status(task_id)
        
        if not task_info:
            logger.warning("task_not_found", task_id=task_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        # 결과 데이터 변환
        result_data = None
        if task_info.status == TaskStatus.COMPLETED and task_info.result:
            try:
                result_data = UnderwriteResult(**task_info.result)
            except Exception as e:
                logger.warning("result_conversion_failed", 
                              task_id=task_id,
                              error=str(e))
                # 변환 실패 시 원본 데이터 그대로 사용
                result_data = task_info.result
        
        # TaskStatusResponse 생성
        response = TaskStatusResponse(
            task_id=task_info.task_id,
            request_id=task_info.request_id,
            status=task_info.status,
            priority=task_info.priority,
            created_at=task_info.created_at,
            started_at=task_info.started_at,
            completed_at=task_info.completed_at,
            processing_duration=task_info.processing_duration,
            progress=task_info.progress,
            estimated_completion=task_info.estimated_completion,
            result=result_data,
            error=task_info.error,
            callback_status=task_info.callback_status,
            callback_attempts=task_info.callback_attempts,
            last_callback_attempt=task_info.last_callback_attempt
        )
        
        logger.info("task_status_retrieved", 
                   task_id=task_id,
                   status=task_info.status.value,
                   progress_percentage=task_info.progress.percentage)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("task_status_retrieval_error", 
                    task_id=task_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving task status"
        )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(
    task_id: str = Path(..., description="작업 고유 ID", min_length=10, max_length=100)
):
    """
    작업 취소
    
    처리 중이거나 대기 중인 작업을 취소합니다.
    이미 완료되었거나 실패한 작업은 취소할 수 없습니다.
    """
    
    logger.info("task_cancellation_requested", task_id=task_id)
    
    try:
        task_manager = get_task_manager()
        
        # 작업 존재 여부 확인
        task_info = await task_manager.get_task_status(task_id)
        if not task_info:
            logger.warning("task_not_found_for_cancellation", task_id=task_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        # 취소 가능 여부 확인
        if task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            logger.warning("task_cannot_be_cancelled", 
                          task_id=task_id,
                          current_status=task_info.status.value)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task {task_id} cannot be cancelled (current status: {task_info.status.value})"
            )
        
        # 작업 취소
        cancelled = await task_manager.cancel_task(task_id)
        
        if cancelled:
            logger.info("task_cancelled_successfully", task_id=task_id)
            # 204 No Content 반환
            return None
        else:
            logger.error("task_cancellation_failed", task_id=task_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel task"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("task_cancellation_error", 
                    task_id=task_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while cancelling task"
        )


@router.get("/tasks", status_code=status.HTTP_200_OK)
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(default=None, description="상태별 필터"),
    limit: int = Query(default=50, ge=1, le=1000, description="반환할 작업 수 제한"),
    include_completed: bool = Query(default=True, description="완료된 작업 포함 여부")
):
    """
    작업 목록 조회
    
    시스템의 작업들을 조회합니다. 상태별 필터링과 페이징을 지원합니다.
    """
    
    logger.info("task_list_requested", 
               status_filter=status_filter.value if status_filter else None,
               limit=limit,
               include_completed=include_completed)
    
    try:
        task_manager = get_task_manager()
        
        # 완료된 작업 제외 옵션 처리
        if not include_completed and not status_filter:
            # 완료되지 않은 작업들만 조회
            active_statuses = [
                TaskStatus.ACCEPTED,
                TaskStatus.QUEUED, 
                TaskStatus.PROCESSING
            ]
            all_tasks = []
            for status in active_statuses:
                tasks = await task_manager.list_tasks(limit=limit, status_filter=status)
                all_tasks.extend(tasks)
            
            # 생성 시간 역순 정렬 후 제한
            all_tasks.sort(key=lambda x: x.created_at, reverse=True)
            tasks = all_tasks[:limit]
        else:
            # 일반 조회
            tasks = await task_manager.list_tasks(limit=limit, status_filter=status_filter)
        
        # 응답 형태로 변환
        task_summaries = []
        for task_info in tasks:
            summary = {
                "task_id": task_info.task_id,
                "request_id": task_info.request_id,
                "status": task_info.status.value,
                "priority": task_info.priority,
                "created_at": task_info.created_at,
                "started_at": task_info.started_at,
                "completed_at": task_info.completed_at,
                "processing_duration": task_info.processing_duration,
                "progress_percentage": task_info.progress.percentage,
                "current_step": task_info.progress.current_step,
                "callback_status": task_info.callback_status.value,
                "has_result": task_info.result is not None,
                "has_error": task_info.error is not None
            }
            task_summaries.append(summary)
        
        response = {
            "tasks": task_summaries,
            "total_count": len(task_summaries),
            "filters": {
                "status": status_filter.value if status_filter else None,
                "limit": limit,
                "include_completed": include_completed
            },
            "timestamp": datetime.utcnow()
        }
        
        logger.info("task_list_retrieved", 
                   returned_count=len(task_summaries),
                   status_filter=status_filter.value if status_filter else None)
        
        return response
        
    except Exception as e:
        logger.error("task_list_retrieval_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving task list"
        )


@router.post("/tasks/{task_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_failed_task(
    task_id: str = Path(..., description="작업 고유 ID", min_length=10, max_length=100)
):
    """
    실패한 작업 재시도
    
    실패한 작업을 다시 큐에 추가하여 재처리합니다.
    """
    
    logger.info("task_retry_requested", task_id=task_id)
    
    try:
        task_manager = get_task_manager()
        
        # 작업 존재 여부 및 상태 확인
        task_info = await task_manager.get_task_status(task_id)
        if not task_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        if task_info.status != TaskStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task {task_id} cannot be retried (current status: {task_info.status.value})"
            )
        
        # 새로운 작업 ID로 재제출
        from ..services.underwriter_service import get_underwriter_service
        from ..models import UnderwriteRequest
        
        underwriter_service = get_underwriter_service()
        original_request = UnderwriteRequest(**task_info.request_data)
        
        new_task_id = await task_manager.submit_task(
            request=original_request,
            task_processor=underwriter_service.process_underwrite_request
        )
        
        logger.info("task_retried_successfully", 
                   original_task_id=task_id,
                   new_task_id=new_task_id)
        
        return {
            "message": "Task retry submitted successfully",
            "original_task_id": task_id,
            "new_task_id": new_task_id,
            "status_url": f"/api/v1/tasks/{new_task_id}",
            "timestamp": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("task_retry_error", 
                    task_id=task_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrying task"
        )