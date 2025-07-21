"""
FastAPI Main Application
LLM-Lite Underwriter API 서버
"""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from .config import get_api_settings
from .models import ErrorResponse
from .middleware.logging import setup_logging, LoggingMiddleware
from .routes import underwriter, tasks, health, notifications

# 설정 로드
settings = get_api_settings()

# 애플리케이션 시작 시간
startup_time = time.time()

# 전역 상태 관리
app_state: Dict[str, Any] = {
    "startup_time": startup_time,
    "task_manager": None,
    "notification_service": None
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    
    # 시작 시 초기화
    print(f"🚀 Starting {settings.title} v{settings.version}")
    print(f"🌐 Server: {settings.host}:{settings.port}")
    print(f"🔧 Debug mode: {settings.debug}")
    
    # 로깅 설정
    setup_logging()
    
    # Task Manager 초기화
    from .services.task_manager import get_task_manager
    task_manager = get_task_manager()
    app_state["task_manager"] = task_manager
    await task_manager.start()
    
    # Notification Service 초기화  
    from .services.notification_service import get_notification_service
    notification_service = get_notification_service()
    app_state["notification_service"] = notification_service
    
    # 결과 디렉터리 생성
    import os
    os.makedirs(settings.results_output_dir, exist_ok=True)
    os.makedirs(settings.log_output_dir, exist_ok=True)
    os.makedirs(settings.file_output_directory, exist_ok=True)
    
    print("✅ Application startup complete")
    
    yield  # 애플리케이션 실행
    
    # 종료 시 정리
    print("🛑 Shutting down application...")
    
    # Task Manager 정리
    if app_state.get("task_manager"):
        await app_state["task_manager"].shutdown()
    
    # Notification Service 정리
    if app_state.get("notification_service"):
        await app_state["notification_service"].close()
    
    print("✅ Application shutdown complete")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Processing-Time"]
)

# 로깅 미들웨어
app.add_middleware(LoggingMiddleware)

# Trusted Host 미들웨어 (프로덕션 환경)
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # 프로덕션에서는 실제 호스트로 제한
    )


# 전역 예외 처리기
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 처리"""
    error_response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={
            "errors": exc.errors(),
            "body": exc.body
        },
        timestamp=datetime.utcnow(),
        request_id=getattr(request.state, 'request_id', None)
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    error_response = ErrorResponse(
        error_code=f"HTTP_{exc.status_code}",
        message=exc.detail,
        timestamp=datetime.utcnow(),
        request_id=getattr(request.state, 'request_id', None)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 처리"""
    error_response = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        details={"error_type": type(exc).__name__} if settings.debug else None,
        timestamp=datetime.utcnow(),
        request_id=getattr(request.state, 'request_id', None)
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )


# 라우터 등록
app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["Health Check"]
)

app.include_router(
    underwriter.router,
    prefix="/api/v1",
    tags=["Underwriter"]
)

app.include_router(
    tasks.router,
    prefix="/api/v1",
    tags=["Tasks"]
)

app.include_router(
    notifications.router,
    prefix="/api/v1/notifications",
    tags=["Notifications"]
)

# 정적 파일 서빙 (문서)
import os
docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
if os.path.exists(docs_path):
    app.mount("/docs-static", StaticFiles(directory=docs_path), name="docs-static")

# 루트 엔드포인트
@app.get("/", include_in_schema=False)
async def root():
    """API 루트"""
    return {
        "service": settings.title,
        "version": settings.version,
        "status": "running",
        "docs_url": "/docs" if settings.debug else "disabled",
        "swagger_docs": "/docs-static/swagger-ui.html",
        "api_spec": "/docs-static/swagger.yaml",
        "timestamp": datetime.utcnow().isoformat()
    }


# 애플리케이션 상태 접근 함수
def get_app_state() -> Dict[str, Any]:
    """애플리케이션 상태 반환"""
    return app_state


def get_startup_time() -> float:
    """시작 시간 반환"""
    return startup_time


# 개발 서버 실행
if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[{time:YYYY-MM-DD HH:mm:ss}] {level} | {name} | {message}",
                    "style": "{",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )