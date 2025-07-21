"""
Health Check Router
시스템 상태 확인 API
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ..models import HealthCheckResponse
from ..config import get_api_settings
from ..main import get_startup_time

router = APIRouter()
settings = get_api_settings()


@router.get("/health", response_model=HealthCheckResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    시스템 Health Check
    
    서비스 상태, 의존성 상태, 시스템 정보를 반환합니다.
    """
    
    current_time = datetime.utcnow()
    uptime_seconds = time.time() - get_startup_time()
    
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
    Kubernetes Readiness Probe
    
    서비스가 트래픽을 받을 준비가 되었는지 확인합니다.
    """
    
    # 핵심 의존성만 확인
    essential_deps = ["openai_api", "underwriter_agent"]
    dependencies_status = await check_dependencies()
    
    ready = all(
        dependencies_status.get(dep, "unhealthy") == "healthy" 
        for dep in essential_deps
    )
    
    if ready:
        return {"status": "ready", "timestamp": datetime.utcnow()}
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready", 
                "timestamp": datetime.utcnow(),
                "failed_dependencies": [
                    dep for dep in essential_deps 
                    if dependencies_status.get(dep, "unhealthy") != "healthy"
                ]
            }
        )


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """
    Kubernetes Liveness Probe
    
    서비스가 살아있는지 확인합니다.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow(),
        "uptime_seconds": time.time() - get_startup_time()
    }


async def check_dependencies() -> Dict[str, str]:
    """의존성 상태 확인"""
    
    dependencies = {}
    
    # 1. OpenAI API 연결 확인
    dependencies["openai_api"] = await check_openai_api()
    
    # 2. UnderwriterAgent 초기화 확인
    dependencies["underwriter_agent"] = await check_underwriter_agent()
    
    # 3. File System 접근 확인
    dependencies["file_system"] = await check_file_system()
    
    # 4. Redis 연결 확인 (설정된 경우)
    if settings.redis_url:
        dependencies["redis"] = await check_redis()
    
    # 5. Task Manager 상태 확인 (구현된 경우)
    dependencies["task_manager"] = await check_task_manager()
    
    return dependencies


async def check_openai_api() -> str:
    """OpenAI API 연결 상태 확인"""
    try:
        # agents.core.config에서 OpenAI API 키 확인
        from agents.core.config import get_config
        config = get_config()
        
        if not config.openai_api_key:
            return "unhealthy"
        
        # 실제 API 호출 대신 설정만 확인 (비용 절약)
        if config.validate():
            return "healthy"
        else:
            return "unhealthy"
            
    except Exception:
        return "unhealthy"


async def check_underwriter_agent() -> str:
    """UnderwriterAgent 초기화 가능성 확인"""
    try:
        from agents.underwriter_agent import UnderwriterAgent
        
        # 간단한 인스턴스 생성 테스트 (실제 실행은 하지 않음)
        agent = UnderwriterAgent(simulation_years=10)  # 최소 설정
        
        # 그래프가 올바르게 생성되었는지 확인
        if hasattr(agent, 'graph') and agent.graph is not None:
            return "healthy"
        else:
            return "unhealthy"
            
    except Exception:
        return "unhealthy"


async def check_file_system() -> str:
    """파일 시스템 접근 확인"""
    try:
        import os
        import tempfile
        
        # 결과 디렉터리 쓰기 권한 확인
        if not os.path.exists(settings.results_output_dir):
            os.makedirs(settings.results_output_dir, exist_ok=True)
        
        # 임시 파일 생성/삭제 테스트
        with tempfile.NamedTemporaryFile(dir=settings.results_output_dir, delete=True):
            pass
        
        return "healthy"
        
    except Exception:
        return "unhealthy"


async def check_redis() -> str:
    """Redis 연결 확인"""
    try:
        import redis.asyncio as redis
        
        # Redis 클라이언트 생성 및 연결 테스트
        client = redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            db=settings.redis_db
        )
        
        # 간단한 ping 테스트
        await asyncio.wait_for(client.ping(), timeout=5.0)
        await client.close()
        
        return "healthy"
        
    except Exception:
        return "unhealthy"


async def check_task_manager() -> str:
    """Task Manager 상태 확인"""
    try:
        # Task Manager가 구현되면 여기서 상태 확인
        # 현재는 항상 healthy 반환 (Phase 2에서 구현 예정)
        return "healthy"
        
    except Exception:
        return "unhealthy"


async def get_system_info() -> Dict[str, Any]:
    """시스템 정보 수집 (디버그 모드에서만)"""
    try:
        import psutil
        import platform
        
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_used_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
        
    except ImportError:
        # psutil이 설치되지 않은 경우
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "note": "Install psutil for detailed system info"
        }
        
    except Exception:
        return {"error": "Failed to collect system info"}