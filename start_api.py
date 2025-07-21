#!/usr/bin/env python3
"""
LLM-Lite Underwriter API Startup Script
API 서버를 시작하는 스크립트
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Also add src directory for agents
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

def main():
    """API 서버 시작"""
    
    # 환경 변수 파일 확인
    env_file = project_root / ".env"
    env_api_file = project_root / ".env.api"
    
    if not env_file.exists() and not env_api_file.exists():
        print("⚠️  Environment file not found!")
        print(f"Please copy .env.api.example to .env and configure it:")
        print(f"  cp .env.api.example .env")
        print()
        print("Required configuration:")
        print("  - OPENAI_API_KEY: Your OpenAI API key")
        print("  - API_* settings: Server configuration")
        return 1
    
    # API 의존성 확인
    try:
        import fastapi
        import uvicorn
        import pydantic
        print(f"✅ FastAPI {fastapi.__version__}")
        print(f"✅ Uvicorn {uvicorn.__version__}")
        print(f"✅ Pydantic {pydantic.__version__}")
    except ImportError as e:
        print(f"❌ Missing API dependencies: {e}")
        print("Please install API dependencies:")
        print("  pip install fastapi uvicorn pydantic python-multipart")
        return 1
    
    # agents 모듈 확인
    try:
        from agents.core.config import get_config
        from agents.underwriter_agent import UnderwriterAgent
        print("✅ UnderwriterAgent available")
    except ImportError as e:
        print(f"❌ Cannot import agents: {e}")
        print("Please ensure the agents module is properly installed")
        return 1
    
    # OpenAI API 키 확인
    try:
        config = get_config()
        if not config.openai_api_key:
            print("❌ OPENAI_API_KEY not set!")
            print("Please set your OpenAI API key in the .env file")
            return 1
        print("✅ OpenAI API key configured")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return 1
    
    # API 서버 시작
    print()
    print("🚀 Starting LLM-Lite Underwriter API...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/api/v1/health")
    print()
    
    try:
        import uvicorn
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 API server stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Failed to start API server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())