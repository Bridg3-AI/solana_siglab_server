"""
Logging Middleware
API 요청/응답 로깅 및 기존 structlog 시스템 통합
"""

import time
import uuid
import json
from typing import Callable
from datetime import datetime

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_logging_settings
from agents.core.logging import get_logger  # 기존 로깅 시스템 활용

settings = get_logging_settings()


class LoggingMiddleware(BaseHTTPMiddleware):
    """API 로깅 미들웨어"""
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.logger = get_logger("api_middleware")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 및 로깅"""
        
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 시작 시간 기록
        start_time = time.time()
        
        # 클라이언트 정보 수집
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # 요청 로깅
        await self._log_request(request, request_id, client_ip, user_agent)
        
        # 요청 처리
        try:
            response = await call_next(request)
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # 응답 로깅
            await self._log_response(request, response, request_id, processing_time)
            
            # 응답 헤더에 메타데이터 추가
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
            
            return response
            
        except Exception as exc:
            processing_time = time.time() - start_time
            
            # 에러 로깅
            await self._log_error(request, exc, request_id, processing_time)
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # Proxy 환경을 고려한 IP 추출
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _log_request(self, request: Request, request_id: str, client_ip: str, user_agent: str):
        """요청 로깅"""
        
        # 요청 본문 크기 체크 (보안을 위해 큰 요청은 로깅하지 않음)
        content_length = request.headers.get("content-length", "0")
        body_size = int(content_length) if content_length.isdigit() else 0
        
        log_data = {
            "event": "api_request_started",
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": self._filter_headers(dict(request.headers)),
            "body_size": body_size,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 설정에 따라 추가 정보 포함
        if settings.include_ip_address:
            log_data["client_ip"] = client_ip
        
        if settings.include_user_agent:
            log_data["user_agent"] = user_agent
        
        # 민감하지 않은 소량의 요청만 본문 로깅
        if (body_size > 0 and body_size < 1024 and  # 1KB 미만
            request.method in ["POST", "PUT", "PATCH"] and
            "application/json" in request.headers.get("content-type", "")):
            
            try:
                # 요청 본문 읽기 (한 번만 읽을 수 있으므로 주의)
                body = await request.body()
                if body:
                    body_json = json.loads(body.decode())
                    # 민감 정보 필터링
                    log_data["request_body"] = self._filter_request_body(body_json)
            except (json.JSONDecodeError, UnicodeDecodeError):
                log_data["request_body"] = "[non-json-body]"
            except Exception:
                log_data["request_body"] = "[body-read-error]"
        
        self.logger.info("api_request_received", **log_data)
    
    async def _log_response(self, request: Request, response: Response, request_id: str, processing_time: float):
        """응답 로깅"""
        
        log_data = {
            "event": "api_request_completed",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "processing_time": round(processing_time, 3),
            "response_headers": self._filter_headers(dict(response.headers)),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 성공/실패 분류
        if 200 <= response.status_code < 400:
            self.logger.info("api_request_success", **log_data)
        elif 400 <= response.status_code < 500:
            self.logger.warning("api_request_client_error", **log_data)
        else:
            self.logger.error("api_request_server_error", **log_data)
    
    async def _log_error(self, request: Request, exception: Exception, request_id: str, processing_time: float):
        """에러 로깅"""
        
        log_data = {
            "event": "api_request_exception",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "processing_time": round(processing_time, 3),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.error("api_request_failed", **log_data)
    
    def _filter_headers(self, headers: dict) -> dict:
        """민감한 헤더 필터링"""
        sensitive_headers = {
            "authorization", "x-api-key", "cookie", "x-auth-token",
            "x-csrf-token", "x-session-id", "proxy-authorization"
        }
        
        filtered = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in sensitive_headers:
                filtered[key] = "[REDACTED]"
            elif "password" in key_lower or "secret" in key_lower or "token" in key_lower:
                filtered[key] = "[REDACTED]"
            else:
                filtered[key] = value
        
        return filtered
    
    def _filter_request_body(self, body: dict) -> dict:
        """요청 본문에서 민감한 정보 필터링"""
        if not isinstance(body, dict):
            return body
        
        sensitive_fields = {
            "password", "token", "api_key", "secret", "auth", "credential"
        }
        
        filtered = {}
        for key, value in body.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered[key] = self._filter_request_body(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                filtered[key] = [self._filter_request_body(item) if isinstance(item, dict) else item for item in value]
            else:
                filtered[key] = value
        
        return filtered


def setup_logging():
    """로깅 시스템 초기화"""
    
    # 기존 agents.core.logging 시스템이 이미 structlog를 설정했으므로
    # 추가 설정만 수행
    
    import logging
    import sys
    from pathlib import Path
    
    # 로그 디렉터리 생성
    log_dir = Path(settings.log_output_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # API 전용 로거 레벨 설정
    api_logger = logging.getLogger("api_middleware")
    api_logger.setLevel(getattr(logging, settings.level.upper()))
    
    # 파일 핸들러 (회전 로그)
    if settings.file_enabled:
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler(
            filename=settings.file_path,
            maxBytes=settings.file_max_size_mb * 1024 * 1024,
            backupCount=settings.file_backup_count,
            encoding='utf-8'
        )
        
        file_handler.setLevel(getattr(logging, settings.level.upper()))
        api_logger.addHandler(file_handler)
    
    print(f"📝 Logging initialized - Level: {settings.level}, Format: {settings.format}")
    
    return api_logger