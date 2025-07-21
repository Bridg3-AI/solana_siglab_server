#!/usr/bin/env python3
"""
Google Cloud Run용 메인 엔트리포인트
LLM-Lite Underwriter API 서버 런처
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수 설정
os.environ.setdefault("PYTHONPATH", str(project_root))

# Google Cloud Run 환경에서는 포트가 환경변수로 제공됨
port = int(os.environ.get("PORT", 8000))
host = os.environ.get("HOST", "0.0.0.0")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)

logger = logging.getLogger(__name__)

def create_app():
    """FastAPI 애플리케이션 인스턴스 생성"""
    try:
        # api.main에서 app 인스턴스 가져오기
        from api.main import app
        
        logger.info(f"🚀 LLM-Lite Underwriter API started")
        logger.info(f"🌐 Server: {host}:{port}")
        logger.info(f"📂 Project root: {project_root}")
        
        return app
        
    except ImportError as e:
        logger.error(f"Failed to import API module: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create app: {e}")
        raise

# FastAPI 애플리케이션 인스턴스 (Cloud Run이 찾는 변수)
app = create_app()

if __name__ == "__main__":
    # 개발 환경에서 직접 실행할 때
    import uvicorn
    
    logger.info("Starting development server...")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Cloud Run에서는 reload 비활성화
        log_level="info",
        access_log=True,
        server_header=False,
        date_header=False
    )