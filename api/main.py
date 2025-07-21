"""
FastAPI Main Application
LLM-Lite Underwriter API 서버
"""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# 간단한 설정
try:
    from .config import get_api_settings
    settings = get_api_settings()
except ImportError:
    # 폴백 설정
    class SimpleSettings:
        title = "LLM-Lite Underwriter API"
        version = "1.0.0"
        description = "파라메트릭 보험 자동 인수심사 API"
        debug = True
        
    settings = SimpleSettings()

# 애플리케이션 시작 시간
startup_time = time.time()

# 전역 상태 관리 (단순화)
app_state: Dict[str, Any] = {
    "startup_time": startup_time,
}


# FastAPI 애플리케이션 생성 (단순화)
app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    docs_url="/docs" if getattr(settings, 'debug', True) else None,
    redoc_url="/redoc" if getattr(settings, 'debug', True) else None,
)

# CORS 미들웨어 (단순화)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 단순화된 예외 처리기
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 처리"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 처리"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# 라우터 등록 (단순화 - health만 우선)
try:
    from .routes import health
    app.include_router(
        health.router,
        prefix="/api/v1",
        tags=["Health Check"]
    )
    print("✅ Health router loaded")
except ImportError as e:
    print(f"⚠️ Could not load health router: {e}")

# 다른 라우터들은 점진적으로 추가
try:
    from .routes import underwriter
    app.include_router(
        underwriter.router,
        prefix="/api/v1",
        tags=["Underwriter"]
    )
    print("✅ Underwriter router loaded")
except ImportError as e:
    print(f"⚠️ Could not load underwriter router: {e}")

try:
    from .routes import tasks
    app.include_router(
        tasks.router,
        prefix="/api/v1",
        tags=["Tasks"]
    )
    print("✅ Tasks router loaded")
except ImportError as e:
    print(f"⚠️ Could not load tasks router: {e}")

try:
    from .routes import notifications
    app.include_router(
        notifications.router,
        prefix="/api/v1/notifications",
        tags=["Notifications"]
    )
    print("✅ Notifications router loaded")
except ImportError as e:
    print(f"⚠️ Could not load notifications router: {e}")

# 루트 엔드포인트 (단순화)
@app.get("/", include_in_schema=False)
async def root():
    """API 루트"""
    return {
        "service": settings.title,
        "version": settings.version,
        "status": "running",
        "docs_url": "/docs",
        "timestamp": datetime.utcnow().isoformat()
    }


# 애플리케이션 상태 접근 함수 (단순화)
def get_app_state() -> Dict[str, Any]:
    """애플리케이션 상태 반환"""
    return app_state


def get_startup_time() -> float:
    """시작 시간 반환"""
    return startup_time


# 개발 서버 실행 (단순화)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=getattr(settings, 'host', '0.0.0.0'),
        port=getattr(settings, 'port', 8000),
        reload=getattr(settings, 'debug', True),
    )