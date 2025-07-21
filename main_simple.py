#!/usr/bin/env python3
"""
Google Cloud Run용 간단한 엔트리포인트
최소한의 의존성으로 FastAPI 앱 로딩
"""

import sys
import os
from pathlib import Path

# Python 경로 설정
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# 최소한의 FastAPI 앱 생성
try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI(
        title="LLM-Lite Underwriter API",
        description="파라메트릭 보험 자동 인수심사 API",
        version="1.0.0"
    )
    
    @app.get("/")
    async def root():
        return {"message": "LLM-Lite Underwriter API is running", "status": "ok"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "timestamp": "2025-01-21T12:00:00Z"}
    
    print("✅ Simple FastAPI app created successfully")
    
except ImportError as e:
    print(f"❌ Failed to create simple app: {e}")
    raise

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)