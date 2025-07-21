#!/bin/bash
echo "🚀 Starting with uvicorn (forcing over gunicorn)"
exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}