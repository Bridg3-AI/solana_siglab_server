# LLM-Lite Underwriter API 사용 가이드

LLM-Lite Underwriter API는 자연어 입력을 통해 파라메트릭 보험상품을 자동으로 설계하는 인수심사 시스템입니다.

## 📋 목차

1. [API 개요](#api-개요)
2. [서버 실행](#서버-실행)
3. [주요 엔드포인트](#주요-엔드포인트)
4. [인수심사 요청 예시](#인수심사-요청-예시)
5. [Webhook 설정](#webhook-설정)
6. [작업 상태 모니터링](#작업-상태-모니터링)
7. [에러 처리](#에러-처리)
8. [테스트 실행](#테스트-실행)

## API 개요

### 주요 기능
- **자연어 입력**: 한국어로 보험상품 요구사항을 입력
- **비동기 처리**: 백그라운드에서 인수심사 진행
- **실시간 진행률**: 처리 단계별 진행 상황 확인
- **외부 알림**: Webhook/파일/메시지큐를 통한 결과 전송
- **배치 처리**: 여러 요청을 한 번에 처리

### 아키텍처
```
Client Request → API Gateway → Task Queue → UnderwriterAgent → Result → Notification
```

## 서버 실행

### 개발 환경 실행
```bash
# API 의존성 설치
pip install -r requirements-api.txt

# 서버 실행
cd /path/to/project
python -m api.main

# 또는 uvicorn 직접 실행
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 환경 변수 설정 (.env)
```env
# 서버 설정
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# 작업 관리
API_MAX_CONCURRENT_TASKS=10
API_TASK_TIMEOUT=600

# Webhook 설정
WEBHOOK_TIMEOUT=30
WEBHOOK_MAX_RETRIES=3

# 파일 출력 설정
API_NOTIFICATION_FILE_DIR=./api_notifications
```

## 주요 엔드포인트

### 1. 헬스 체크
```http
GET /api/v1/health
```

### 2. 인수심사 요청
```http
POST /api/v1/underwrite
Content-Type: application/json
```

### 3. 작업 상태 조회
```http
GET /api/v1/tasks/{task_id}
```

### 4. 작업 목록 조회
```http
GET /api/v1/tasks?status_filter=completed&limit=10
```

### 5. Webhook 연결 테스트
```http
POST /api/v1/notifications/test-webhook
```

### 6. 알림 통계 조회
```http
GET /api/v1/notifications/stats
```

## 인수심사 요청 예시

### 기본 요청
```json
{
  "request_id": "typhoon_insurance_001",
  "user_input": "태풍으로 인한 농작물 손실에 대한 파라메트릭 보험상품을 설계해주세요. 풍속 40m/s 이상일 때 보험금이 지급되도록 하고, 보장 금액은 1억원으로 설정해주세요.",
  "callback": {
    "type": "webhook",
    "webhook": {
      "url": "https://your-server.com/webhook/callback",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN",
        "Content-Type": "application/json"
      }
    }
  },
  "options": {
    "simulation_years": 1000,
    "market_risk_premium": 0.15,
    "debug_mode": false,
    "enable_audit_trail": true
  },
  "priority": "high"
}
```

### 응답
```json
{
  "task_id": "underwriter_20250121_143052_a1b2c3d4",
  "request_id": "typhoon_insurance_001",
  "status": "accepted",
  "estimated_duration_seconds": 90,
  "created_at": "2025-01-21T14:30:52.123456",
  "status_url": "/api/v1/tasks/underwriter_20250121_143052_a1b2c3d4"
}
```

## Webhook 설정

### Webhook 페이로드 예시
```json
{
  "task_id": "underwriter_20250121_143052_a1b2c3d4",
  "request_id": "typhoon_insurance_001",
  "status": "completed",
  "completed_at": "2025-01-21T14:32:15.654321",
  "processing_duration": 83.5,
  "timestamp": "2025-01-21T14:32:15.654321",
  "result": {
    "expected_loss": 15000000,
    "gross_premium": 18750000,
    "risk_level": "medium",
    "loss_ratio": 0.8,
    "coefficient_of_variation": 1.25,
    "var_99": 85000000,
    "tvar_99": 92000000,
    "simulation_years": 1000,
    "validation_passed": true,
    "event_type": "태풍",
    "recommendation": "추천: 보험료 조정 후 인수 가능"
  },
  "summary": {
    "expected_loss": 15000000,
    "gross_premium": 18750000,
    "risk_level": "medium",
    "loss_ratio": 0.8
  }
}
```

### 파일 시스템 출력
```json
{
  "callback": {
    "type": "file_system"
  }
}
```
결과는 `./api_notifications/` 디렉터리에 JSON 파일로 저장됩니다.

## 작업 상태 모니터링

### 상태 종류
- `accepted`: 요청 접수
- `queued`: 큐 대기 중
- `processing`: 처리 중
- `completed`: 완료
- `failed`: 실패
- `cancelled`: 취소됨

### 진행률 확인
```json
{
  "progress": {
    "percentage": 65.0,
    "current_step": "pricing_calculation",
    "completed_steps": ["peril_canvas", "prior_extraction", "scenario_generation"],
    "total_steps": 5
  }
}
```

### 작업 취소
```http
DELETE /api/v1/tasks/{task_id}
```

## 에러 처리

### 에러 응답 형식
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": {
    "errors": [
      {
        "loc": ["user_input"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  },
  "timestamp": "2025-01-21T14:30:52.123456",
  "request_id": "req_123456"
}
```

### 일반적인 에러 코드
- `VALIDATION_ERROR`: 요청 데이터 검증 실패
- `QUEUE_FULL`: 작업 큐가 가득 참
- `TASK_NOT_FOUND`: 작업을 찾을 수 없음
- `TIMEOUT`: 작업 처리 시간 초과
- `INTERNAL_SERVER_ERROR`: 서버 내부 오류

## 테스트 실행

### API 테스트 스크립트
```bash
# 테스트 실행
python scripts/test_api.py

# 결과 확인
cat api_test_results.json
```

### 수동 테스트 예시 (curl)
```bash
# 헬스 체크
curl -X GET "http://localhost:8000/api/v1/health"

# 인수심사 요청
curl -X POST "http://localhost:8000/api/v1/underwrite" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test_001",
    "user_input": "지진 보험상품을 설계해주세요",
    "callback": {"type": "file_system"},
    "options": {"simulation_years": 500}
  }'

# 작업 상태 확인
curl -X GET "http://localhost:8000/api/v1/tasks/TASK_ID"
```

## 성능 최적화 팁

1. **동시 요청 제한**: `API_MAX_CONCURRENT_TASKS` 환경변수로 조절
2. **시뮬레이션 연수**: 정확도와 처리 시간의 균형점 찾기
3. **Webhook 타임아웃**: 안정적인 외부 엔드포인트 사용
4. **배치 처리**: 여러 요청을 한 번에 제출

## 문제 해결

### 일반적인 문제
1. **서버 시작 실패**: 포트 충돌 확인
2. **작업 처리 느림**: 시뮬레이션 연수 조정
3. **Webhook 실패**: 대상 URL 접근성 확인
4. **메모리 부족**: 동시 작업 수 제한

### 로그 확인
```bash
# API 로그 확인
tail -f ./api_logs/api.log

# 시스템 상태 확인
curl "http://localhost:8000/api/v1/underwrite/stats"
```

---

📞 **지원**: 문제가 발생하면 GitHub Issues 또는 개발팀에 문의하세요.
🔗 **API 문서**: http://localhost:8000/docs (개발 모드에서만 활성화)