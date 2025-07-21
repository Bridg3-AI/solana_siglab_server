# Google Cloud Run용 Dockerfile
# LLM-Lite Underwriter API

# Python 3.11 슬림 베이스 이미지 (Cloud Run 최적화)
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="LLM-Lite Development Team"
LABEL description="파라메트릭 보험 자동 인수심사 API"
LABEL version="1.0.0"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# 작업 디렉터리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python 의존성 설치 (레이어 캐싱 최적화)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip cache purge

# 애플리케이션 코드 복사
COPY . .

# 불필요한 파일 제거 (.dockerignore와 함께 사용)
RUN rm -rf \
    tests/ \
    *.md \
    .git \
    .env* \
    node_modules/ \
    __pycache__/ \
    .pytest_cache/ \
    *.pyc \
    *.pyo

# 로그 및 결과 디렉터리 생성
RUN mkdir -p /app/api_logs /app/api_results /app/api_notifications

# 비루트 사용자 생성 (보안 강화)
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/api/v1/health || exit 1

# Cloud Run에서 제공하는 PORT 환경변수 사용
ENV PORT=8080
EXPOSE $PORT

# 애플리케이션 실행
# Cloud Run은 gunicorn 사용 권장
CMD exec gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker --timeout 0 main:app