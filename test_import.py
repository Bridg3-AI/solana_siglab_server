#!/usr/bin/env python3
"""
main.py import 테스트 스크립트
"""

import sys
from pathlib import Path

# 현재 디렉터리를 Python 경로에 추가
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

print(f"Current directory: {current_dir}")
print(f"Python path: {sys.path[:3]}")

try:
    print("Testing import of main module...")
    import main
    print(f"✅ Successfully imported main module")
    print(f"✅ App object: {type(main.app)}")
    print(f"✅ App object available: {'app' in dir(main)}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()