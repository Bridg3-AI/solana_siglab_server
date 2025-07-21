#!/usr/bin/env python3
"""
Google Cloud Run용 메인 엔트리포인트
LLM-Lite Underwriter API 서버 런처
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 최상위로 추가
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# 환경 변수 확실히 설정
os.environ["PYTHONPATH"] = str(current_dir)

# 간단하고 확실한 앱 로딩
try:
    from api.main import app
    print(f"✅ Successfully loaded app from: {current_dir}")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current directory: {current_dir}")
    print(f"Python path: {sys.path}")
    print(f"Directory contents: {os.listdir(current_dir)}")
    if (current_dir / "api").exists():
        print(f"API directory contents: {os.listdir(current_dir / 'api')}")
    raise

# gunicorn이 찾을 변수
__all__ = ["app"]

if __name__ == "__main__":
    # 개발 환경에서 직접 실행할 때
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting development server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )