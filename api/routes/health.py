"""
Health Check Router
시스템 상태 확인 API
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any

# 시작 시간을 모듈 레벨에서 기록
_startup_time = time.time()

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ..models import HealthCheckResponse
from ..config import get_api_settings

router = APIRouter()
settings = get_api_settings()


@router.get("/health", response_model=HealthCheckResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    시스템 Health Check
    
    서비스 상태, 의존성 상태, 시스템 정보를 반환합니다.
    """
    
    current_time = datetime.utcnow()
    uptime_seconds = time.time() - _startup_time
    
    # 의존성 상태 확인
    dependencies_status = await check_dependencies()
    
    # 전체 상태 결정
    overall_status = "healthy" if all(
        status == "healthy" for status in dependencies_status.values()
    ) else "unhealthy"
    
    # 시스템 정보 수집
    system_info = await get_system_info() if settings.debug else None
    
    health_response = HealthCheckResponse(
        status=overall_status,
        timestamp=current_time,
        version=settings.version,
        uptime_seconds=uptime_seconds,
        dependencies=dependencies_status,
        system_info=system_info
    )
    
    # 상태에 따른 HTTP 상태 코드 결정
    status_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content=health_response.dict()
    )


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe():
    """
    Kubernetes Readiness Probe (간소화)
    
    서비스가 트래픽을 받을 준비가 되었는지 확인합니다.
    """
    return {"status": "ready", "timestamp": datetime.utcnow()}


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """
    Kubernetes Liveness Probe
    
    서비스가 살아있는지 확인합니다.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow(),
        "uptime_seconds": time.time() - _startup_time
    }


async def check_dependencies() -> Dict[str, str]:
    """의존성 상태 확인 (간소화 버전)"""
    
    dependencies = {}
    
    try:
        # 기본적인 시스템 상태만 확인
        dependencies["system"] = "healthy"
        dependencies["api_server"] = "healthy"
        
        # 파일 시스템만 간단하게 확인
        import os
        if os.access(".", os.W_OK):
            dependencies["file_system"] = "healthy"
        else:
            dependencies["file_system"] = "unhealthy"
            
    except Exception:
        dependencies["system"] = "unhealthy"
    
    return dependencies


async def get_system_info() -> Dict[str, Any]:
    """시스템 정보 수집 (간소화 버전)"""
    try:
        import platform
        
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "note": "Simplified health check for Cloud Run"
        }
        
    except Exception:
        return {"error": "Failed to collect system info"}