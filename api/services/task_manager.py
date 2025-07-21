"""
Task Manager
비동기 작업 큐 및 상태 관리 시스템
"""

import asyncio
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Awaitable
from enum import Enum
import threading
from dataclasses import dataclass, field

from agents.core.logging import get_logger
from ..models import TaskStatus, CallbackStatus, TaskProgress, ProcessingStep, UnderwriteRequest, CallbackConfig, TaskStatusResponse
from ..config import get_api_settings

settings = get_api_settings()
logger = get_logger("task_manager")


@dataclass
class TaskInfo:
    """작업 정보"""
    task_id: str
    request_id: str
    status: TaskStatus
    priority: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 요청 정보
    request_data: Dict[str, Any] = field(default_factory=dict)
    callback_config: Optional[Dict[str, Any]] = None
    
    # 진행 상황
    progress: TaskProgress = field(default_factory=lambda: TaskProgress(
        current_step=None,
        completed_steps=[],
        total_steps=5,
        percentage=0.0,
        steps=[]
    ))
    
    # 결과 및 에러
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # 콜백 상태
    callback_status: CallbackStatus = CallbackStatus.PENDING
    callback_attempts: int = 0
    last_callback_attempt: Optional[datetime] = None
    
    # 메타데이터
    processing_duration: Optional[float] = None
    estimated_completion: Optional[datetime] = None
    timeout_at: Optional[datetime] = None
    
    def update_progress(self, current_step: str, percentage: float):
        """진행률 업데이트"""
        if current_step != self.progress.current_step:
            if self.progress.current_step and self.progress.current_step not in self.progress.completed_steps:
                self.progress.completed_steps.append(self.progress.current_step)
        
        self.progress.current_step = current_step
        self.progress.percentage = min(100.0, max(0.0, percentage))
        
        # 예상 완료 시간 계산
        if self.started_at and percentage > 0:
            elapsed = (datetime.utcnow() - self.started_at).total_seconds()
            estimated_total = elapsed / (percentage / 100)
            self.estimated_completion = self.started_at + timedelta(seconds=estimated_total)
    
    def mark_step_completed(self, step_name: str):
        """단계 완료 표시"""
        if step_name not in self.progress.completed_steps:
            self.progress.completed_steps.append(step_name)
        
        # 진행률 업데이트 (완료된 단계 수 기준)
        self.progress.percentage = (len(self.progress.completed_steps) / self.progress.total_steps) * 100
    
    def add_step_info(self, step: ProcessingStep):
        """단계 세부 정보 추가"""
        # 기존 동일 단계 정보 제거
        self.progress.steps = [s for s in self.progress.steps if s.name != step.name]
        self.progress.steps.append(step)
    
    def is_expired(self) -> bool:
        """작업 만료 확인"""
        if self.timeout_at is None:
            return False
        return datetime.utcnow() > self.timeout_at
    
    def get_processing_duration(self) -> Optional[float]:
        """처리 소요 시간 반환 (초)"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()


class TaskManager:
    """비동기 작업 관리자"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.processing_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.max_concurrent_tasks * 2)
        self.processing_semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)
        self.worker_tasks: List[asyncio.Task] = []
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        
        logger.info("task_manager_initialized", 
                   max_concurrent=settings.max_concurrent_tasks,
                   timeout_seconds=settings.task_timeout_seconds)
    
    async def start(self):
        """Task Manager 시작"""
        if self.running:
            logger.warning("task_manager_already_running")
            return
        
        self.running = True
        logger.info("task_manager_starting")
        
        # 워커 태스크들 시작
        for i in range(settings.max_concurrent_tasks):
            worker_task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(worker_task)
        
        # 정리 태스크 시작
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        logger.info("task_manager_started", workers=len(self.worker_tasks))
    
    async def shutdown(self):
        """Task Manager 종료"""
        if not self.running:
            return
        
        logger.info("task_manager_shutting_down")
        self.running = False
        
        # 모든 워커 태스크 취소
        for worker_task in self.worker_tasks:
            worker_task.cancel()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # 완료 대기
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        if self.cleanup_task:
            await asyncio.gather(self.cleanup_task, return_exceptions=True)
        
        logger.info("task_manager_shutdown_complete")
    
    async def submit_task(
        self, 
        request: UnderwriteRequest, 
        task_processor: Callable[[str, UnderwriteRequest], Awaitable[Dict[str, Any]]]
    ) -> str:
        """작업 제출"""
        
        # 작업 ID 생성
        task_id = f"underwriter_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 타임아웃 시간 계산
        timeout_at = datetime.utcnow() + timedelta(seconds=settings.task_timeout_seconds)
        
        # TaskInfo 생성
        task_info = TaskInfo(
            task_id=task_id,
            request_id=request.request_id,
            status=TaskStatus.ACCEPTED,
            priority=request.priority,
            created_at=datetime.utcnow(),
            request_data=request.dict(),
            callback_config=request.callback.dict() if request.callback else None,
            timeout_at=timeout_at
        )
        
        # 작업 저장
        with self._lock:
            self.tasks[task_id] = task_info
        
        # 큐에 작업 추가
        try:
            queue_item = {
                "task_id": task_id,
                "processor": task_processor,
                "request": request
            }
            
            # 우선순위에 따라 큐 처리 (간단한 구현)
            await self.processing_queue.put(queue_item)
            task_info.status = TaskStatus.QUEUED
            
            logger.info("task_submitted", 
                       task_id=task_id, 
                       request_id=request.request_id,
                       priority=request.priority,
                       queue_size=self.processing_queue.qsize())
            
            return task_id
            
        except asyncio.QueueFull:
            # 큐가 가득 찬 경우
            task_info.status = TaskStatus.FAILED
            task_info.error = "Task queue is full. Please try again later."
            
            logger.error("task_queue_full", 
                        task_id=task_id,
                        queue_size=self.processing_queue.qsize())
            
            raise RuntimeError("Task queue is full")
    
    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """작업 상태 조회"""
        with self._lock:
            return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """작업 취소"""
        with self._lock:
            task_info = self.tasks.get(task_id)
            if not task_info:
                return False
            
            if task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = datetime.utcnow()
            
            logger.info("task_cancelled", task_id=task_id)
            return True
    
    async def list_tasks(self, limit: int = 100, status_filter: Optional[TaskStatus] = None) -> List[TaskInfo]:
        """작업 목록 조회"""
        with self._lock:
            tasks = list(self.tasks.values())
        
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        
        # 생성 시간 역순 정렬
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        return tasks[:limit]
    
    async def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        with self._lock:
            tasks = list(self.tasks.values())
        
        stats = {
            "total_tasks": len(tasks),
            "queue_size": self.processing_queue.qsize(),
            "max_concurrent": settings.max_concurrent_tasks,
            "running_workers": len([t for t in self.worker_tasks if not t.done()]),
            "status_counts": {},
            "avg_processing_time": None
        }
        
        # 상태별 카운트
        for status in TaskStatus:
            count = len([t for t in tasks if t.status == status])
            if count > 0:
                stats["status_counts"][status.value] = count
        
        # 평균 처리 시간 계산
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED and t.processing_duration]
        if completed_tasks:
            stats["avg_processing_time"] = sum(t.processing_duration for t in completed_tasks) / len(completed_tasks)
        
        return stats
    
    async def _worker(self, worker_name: str):
        """워커 프로세스"""
        logger.info("worker_started", worker=worker_name)
        
        while self.running:
            try:
                # 큐에서 작업 가져오기 (타임아웃 설정)
                try:
                    queue_item = await asyncio.wait_for(
                        self.processing_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                task_id = queue_item["task_id"]
                processor = queue_item["processor"]
                request = queue_item["request"]
                
                # 세마포어 획득 (동시 실행 제한)
                async with self.processing_semaphore:
                    await self._process_task(worker_name, task_id, processor, request)
                
            except asyncio.CancelledError:
                logger.info("worker_cancelled", worker=worker_name)
                break
            except Exception as e:
                logger.error("worker_error", worker=worker_name, error=str(e))
                await asyncio.sleep(1)  # 에러 후 잠시 대기
        
        logger.info("worker_stopped", worker=worker_name)
    
    async def _process_task(
        self, 
        worker_name: str, 
        task_id: str, 
        processor: Callable,
        request: UnderwriteRequest
    ):
        """개별 작업 처리"""
        
        task_info = await self.get_task_status(task_id)
        if not task_info:
            logger.error("task_not_found", task_id=task_id)
            return
        
        # 취소된 작업 처리하지 않음
        if task_info.status == TaskStatus.CANCELLED:
            logger.info("task_already_cancelled", task_id=task_id)
            return
        
        # 만료된 작업 처리
        if task_info.is_expired():
            task_info.status = TaskStatus.FAILED
            task_info.error = "Task timeout"
            task_info.completed_at = datetime.utcnow()
            logger.error("task_timeout", task_id=task_id)
            return
        
        logger.info("task_processing_started", 
                   task_id=task_id, 
                   worker=worker_name,
                   request_id=task_info.request_id)
        
        # 작업 시작
        task_info.status = TaskStatus.PROCESSING
        task_info.started_at = datetime.utcnow()
        
        try:
            # 실제 작업 처리
            result = await processor(task_id, request)
            
            # 성공 처리
            task_info.status = TaskStatus.COMPLETED
            task_info.completed_at = datetime.utcnow()
            task_info.result = result
            task_info.processing_duration = task_info.get_processing_duration()
            task_info.progress.percentage = 100.0
            task_info.progress.current_step = "completed"
            
            logger.info("task_processing_completed", 
                       task_id=task_id,
                       processing_duration=task_info.processing_duration)
            
        except Exception as e:
            # 실패 처리
            task_info.status = TaskStatus.FAILED
            task_info.completed_at = datetime.utcnow()
            task_info.error = str(e)
            task_info.processing_duration = task_info.get_processing_duration()
            
            logger.error("task_processing_failed", 
                        task_id=task_id,
                        error=str(e),
                        processing_duration=task_info.processing_duration)
        
        finally:
            # 작업 완료 후 알림 전송 (성공/실패 모두)
            if task_info.callback_config:
                await self._send_completion_notification(task_info)
    
    async def _send_completion_notification(self, task_info: TaskInfo):
        """작업 완료 알림 전송"""
        
        try:
            # 늦은 import로 순환 import 방지
            from .notification_service import get_notification_service
            
            # TaskStatusResponse 생성
            task_status_response = TaskStatusResponse(
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
                result=task_info.result,
                error=task_info.error,
                callback_status=task_info.callback_status,
                callback_attempts=task_info.callback_attempts,
                last_callback_attempt=task_info.last_callback_attempt
            )
            
            # CallbackConfig 재구성
            callback_config = CallbackConfig(**task_info.callback_config)
            
            # 알림 시도 횟수 업데이트
            task_info.callback_attempts += 1
            task_info.last_callback_attempt = datetime.utcnow()
            task_info.callback_status = CallbackStatus.IN_PROGRESS
            
            logger.info("sending_completion_notification", 
                       task_id=task_info.task_id,
                       callback_type=callback_config.type.value,
                       attempt=task_info.callback_attempts)
            
            # 알림 서비스를 통해 전송
            notification_service = get_notification_service()
            notification_result = await notification_service.send_task_completion_notification(
                task_info.task_id,
                task_status_response,
                callback_config
            )
            
            # 결과에 따라 callback_status 업데이트
            if notification_result.get("success", False):
                task_info.callback_status = CallbackStatus.SUCCESS
                logger.info("completion_notification_sent", 
                           task_id=task_info.task_id,
                           callback_type=callback_config.type.value)
            else:
                task_info.callback_status = CallbackStatus.FAILED
                logger.error("completion_notification_failed", 
                           task_id=task_info.task_id,
                           callback_type=callback_config.type.value,
                           error=notification_result.get("error", "Unknown error"))
                
        except Exception as e:
            task_info.callback_status = CallbackStatus.FAILED
            task_info.callback_attempts += 1
            task_info.last_callback_attempt = datetime.utcnow()
            
            logger.error("completion_notification_error", 
                        task_id=task_info.task_id,
                        error=str(e))
    
    async def _cleanup_worker(self):
        """오래된 작업 정리 워커"""
        logger.info("cleanup_worker_started")
        
        while self.running:
            try:
                await self._cleanup_old_tasks()
                
                # 정리 주기 대기
                cleanup_interval = settings.task_cleanup_interval_hours * 3600
                await asyncio.sleep(cleanup_interval)
                
            except asyncio.CancelledError:
                logger.info("cleanup_worker_cancelled")
                break
            except Exception as e:
                logger.error("cleanup_worker_error", error=str(e))
                await asyncio.sleep(300)  # 5분 후 재시도
        
        logger.info("cleanup_worker_stopped")
    
    async def _cleanup_old_tasks(self):
        """오래된 작업 정리"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.task_cleanup_interval_hours)
        
        with self._lock:
            old_task_ids = [
                task_id for task_id, task_info in self.tasks.items()
                if task_info.completed_at and task_info.completed_at < cutoff_time
            ]
            
            for task_id in old_task_ids:
                del self.tasks[task_id]
        
        if old_task_ids:
            logger.info("old_tasks_cleaned", count=len(old_task_ids))


# 전역 TaskManager 인스턴스
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """TaskManager 싱글톤 인스턴스 반환"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager