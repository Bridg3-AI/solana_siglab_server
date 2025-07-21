# ────────────────────────────────
# Google Cloud Run용 Dockerfile
# LLM-Lite Underwriter API
# ────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="LLM-Lite Development Team"
LABEL description="파라메트릭 보험 자동 인수심사 API"
LABEL version="1.0.0"

# ── 런타임 환경 ──────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# ── OS 패키지 ────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python 의존성 ────────────────
COPY requirements.txt .
RUN  pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

# ── 애플리케이션 코드 ────────────
COPY . .

# 필요 없는 파일(테스트·캐시) 제거
RUN rm -rf \
      tests/ *.md .git .env* node_modules/ \
      __pycache__/ .pytest_cache/ *.py[co]

# 로그·아웃풋 디렉터리
RUN mkdir -p /app/api_logs /app/api_results /app/api_notifications

# ── 비루트 사용자 ────────────────
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
EXPOSE 8080

# (선택) HEALTHCHECK – Cloud Run이 무시하지만 로컬 테스트용
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/api/v1/health || exit 1

# ── 실행 엔트리포인트 ─────────────
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", \
     "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "0", \
     "main:app"]