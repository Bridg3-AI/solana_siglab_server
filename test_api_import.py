#!/usr/bin/env python3
"""
api.main import 테스트 (uvicorn 없이)
"""

import sys
from pathlib import Path

# 현재 디렉터리를 Python 경로에 추가
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

print(f"Current directory: {current_dir}")

try:
    print("Testing import of api package...")
    import api
    print(f"✅ Successfully imported api package: {api}")
    
    print("Testing import of api config...")
    from api import config
    print(f"✅ Successfully imported api.config: {config}")
    
    print("Testing import of api models...")
    from api import models
    print(f"✅ Successfully imported api.models: {models}")
    
    # main.py는 uvicorn 의존성 때문에 스킵하고 구조만 확인
    main_file = current_dir / "api" / "main.py" 
    print(f"✅ api/main.py exists: {main_file.exists()}")
    
    # FastAPI 앱이 정의되어 있는지 확인
    with open(main_file, 'r') as f:
        content = f.read()
        if 'app = FastAPI(' in content:
            print("✅ FastAPI app instance found in api/main.py")
        else:
            print("❌ FastAPI app instance not found")
            
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()