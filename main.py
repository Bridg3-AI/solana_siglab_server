#!/usr/bin/env python3
"""
Google Cloud Run용 엔트리포인트
LLM-Lite Underwriter API 서버
"""

import sys
import os
from pathlib import Path

# Python 경로 설정
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

print(f"✅ Python path configured: {current_dir}")

# 단계별 앱 로딩 with 더 상세한 디버깅
try:
    print("📦 Step 1: Loading FastAPI...")
    from fastapi import FastAPI
    print("✅ FastAPI imported successfully")
    
    print("📦 Step 2: Checking api package...")
    import api
    print(f"✅ api package found at: {api.__file__}")
    
    print("📦 Step 3: Loading api.main...")
    from api.main import app
    print("✅ Full API app loaded successfully")
    
except ImportError as e:
    print(f"❌ Failed to load full API app: {e}")
    print("🔄 Falling back to simple FastAPI app...")
    
    # 폴백: 간단한 FastAPI 앱
    from fastapi import FastAPI
    
    app = FastAPI(
        title="LLM-Lite Underwriter API",
        description="파라메트릭 보험 자동 인수심사 API",
        version="1.0.0"
    )
    
    @app.get("/")
    async def root():
        return {"message": "LLM-Lite Underwriter API is running (fallback mode)", "status": "ok"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "timestamp": "2025-01-21T12:00:00Z", "mode": "fallback"}
    
    print("✅ Fallback FastAPI app created")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)