"""
Underwriter Router
인수심사 관련 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, status, Request, Depends
from datetime import datetime
from typing import List

from agents.core.logging import get_logger
from ..models import (
    TaskResponse, 
    UnderwriteRequest, 
    BatchUnderwriteRequest,
    BatchTaskResponse,
    ErrorResponse
)
from ..services.task_manager import get_task_manager
from ..services.underwriter_service import get_underwriter_service
from ..config import get_api_settings

router = APIRouter()
logger = get_logger("underwriter_router")
settings = get_api_settings()


def get_client_info(request: Request):
    """클라이언트 정보 추출"""
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_id": getattr(request.state, 'request_id', None)
    }


@router.post("/underwrite", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_underwrite_request(
    request: UnderwriteRequest,
    client_info: dict = Depends(get_client_info)
):
    """
    인수심사 요청 제출
    
    자연어 보험상품 요청을 받아 비동기로 처리합니다.
    즉시 task_id를 반환하고, 처리 완료 시 callback으로 결과를 전송합니다.
    """
    
    logger.info("underwrite_request_received", 
               request_id=request.request_id,
               user_input_length=len(request.user_input),
               simulation_years=request.options.simulation_years,
               client_ip=client_info["ip"])
    
    try:
        # 서비스 인스턴스 획득
        task_manager = get_task_manager()
        underwriter_service = get_underwriter_service()
        
        # 요청 검증
        validation_error = await underwriter_service.validate_request(request)
        if validation_error:
            logger.warning("request_validation_failed", 
                          request_id=request.request_id,
                          error=validation_error)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=validation_error
            )
        
        # 작업 제출
        task_id = await task_manager.submit_task(
            request=request,
            task_processor=underwriter_service.process_underwrite_request
        )
        
        # 예상 처리 시간 계산
        estimated_duration = await underwriter_service.estimate_processing_time(request)
        
        # 응답 생성
        response = TaskResponse(
            task_id=task_id,
            request_id=request.request_id,
            status="accepted",
            estimated_duration_seconds=estimated_duration,
            created_at=datetime.utcnow(),
            status_url=f"/api/v1/tasks/{task_id}"
        )
        
        logger.info("underwrite_request_accepted", 
                   task_id=task_id,
                   request_id=request.request_id,
                   estimated_duration=estimated_duration)
        
        return response
        
    except HTTPException:
        raise
    except RuntimeError as e:
        if "queue is full" in str(e).lower():
            logger.error("task_queue_full", request_id=request.request_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service is currently busy. Please try again later."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit task for processing"
        )
    except Exception as e:
        logger.error("underwrite_submission_error", 
                    request_id=request.request_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while processing request"
        )


@router.post("/underwrite/batch", response_model=BatchTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_batch_underwrite_request(
    batch_request: BatchUnderwriteRequest,
    client_info: dict = Depends(get_client_info)
):
    """
    배치 인수심사 요청
    
    여러 개의 인수심사 요청을 한 번에 처리합니다.
    각 요청은 독립적인 task_id를 가지며 개별적으로 처리됩니다.
    """
    
    batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(batch_request.requests)}"
    
    logger.info("batch_underwrite_request_received", 
               batch_id=batch_id,
               request_count=len(batch_request.requests),
               client_ip=client_info["ip"])
    
    try:
        task_manager = get_task_manager()
        underwriter_service = get_underwriter_service()
        
        task_responses = []
        
        # 각 요청을 개별적으로 처리
        for i, individual_request in enumerate(batch_request.requests):
            try:
                # 요청 검증
                validation_error = await underwriter_service.validate_request(individual_request)
                if validation_error:
                    logger.warning("batch_item_validation_failed", 
                                  batch_id=batch_id,
                                  item_index=i,
                                  request_id=individual_request.request_id,
                                  error=validation_error)
                    # 검증 실패한 항목은 즉시 실패 응답으로 처리
                    task_responses.append(TaskResponse(
                        task_id=f"failed_{individual_request.request_id}",
                        request_id=individual_request.request_id,
                        status="failed",
                        estimated_duration_seconds=0,
                        created_at=datetime.utcnow(),
                        status_url=f"/api/v1/tasks/failed_{individual_request.request_id}"
                    ))
                    continue
                
                # 정상 요청은 큐에 제출
                task_id = await task_manager.submit_task(
                    request=individual_request,
                    task_processor=underwriter_service.process_underwrite_request
                )
                
                estimated_duration = await underwriter_service.estimate_processing_time(individual_request)
                
                task_responses.append(TaskResponse(
                    task_id=task_id,
                    request_id=individual_request.request_id,
                    status="accepted",
                    estimated_duration_seconds=estimated_duration,
                    created_at=datetime.utcnow(),
                    status_url=f"/api/v1/tasks/{task_id}"
                ))
                
                logger.info("batch_item_accepted", 
                           batch_id=batch_id,
                           item_index=i,
                           task_id=task_id,
                           request_id=individual_request.request_id)
                
            except RuntimeError as e:
                if "queue is full" in str(e).lower():
                    # 큐가 가득 찬 경우 나머지 요청들을 거절
                    logger.error("task_queue_full_during_batch", 
                               batch_id=batch_id,
                               completed_items=len(task_responses))
                    
                    # 나머지 요청들을 실패로 표시
                    for j in range(i, len(batch_request.requests)):
                        remaining_request = batch_request.requests[j]
                        task_responses.append(TaskResponse(
                            task_id=f"rejected_{remaining_request.request_id}",
                            request_id=remaining_request.request_id,
                            status="failed",
                            estimated_duration_seconds=0,
                            created_at=datetime.utcnow(),
                            status_url=f"/api/v1/tasks/rejected_{remaining_request.request_id}"
                        ))
                    break
                else:
                    # 기타 에러
                    task_responses.append(TaskResponse(
                        task_id=f"error_{individual_request.request_id}",
                        request_id=individual_request.request_id,
                        status="failed",
                        estimated_duration_seconds=0,
                        created_at=datetime.utcnow(),
                        status_url=f"/api/v1/tasks/error_{individual_request.request_id}"
                    ))
        
        # 배치 응답 생성
        batch_response = BatchTaskResponse(
            batch_id=batch_id,
            total_tasks=len(batch_request.requests),
            tasks=task_responses,
            created_at=datetime.utcnow()
        )
        
        logger.info("batch_underwrite_request_processed", 
                   batch_id=batch_id,
                   total_requests=len(batch_request.requests),
                   accepted_count=len([t for t in task_responses if t.status == "accepted"]),
                   failed_count=len([t for t in task_responses if t.status == "failed"]))
        
        return batch_response
        
    except Exception as e:
        logger.error("batch_underwrite_submission_error", 
                    batch_id=batch_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while processing batch request"
        )


@router.get("/underwrite/stats", status_code=status.HTTP_200_OK)
async def get_underwriter_stats():
    """
    인수심사 시스템 통계
    
    현재 처리 중인 작업, 큐 상태 등의 통계 정보를 반환합니다.
    """
    
    try:
        task_manager = get_task_manager()
        stats = await task_manager.get_stats()
        
        return {
            "timestamp": datetime.utcnow(),
            "system_status": "operational",
            **stats
        }
        
    except Exception as e:
        logger.error("stats_retrieval_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )