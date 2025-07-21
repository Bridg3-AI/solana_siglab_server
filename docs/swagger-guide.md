# Swagger API 문서 가이드

LLM-Lite Underwriter API의 Swagger 문서를 사용하여 API를 테스트하고 이해하는 방법을 안내합니다.

## 📖 문서 접근 방법

### 1. 서버 실행 후 브라우저에서 접근

```bash
# API 서버 실행
python -m api.main

# 브라우저에서 다음 URL 접근:
# http://localhost:8000/docs-static/swagger-ui.html
```

### 2. 사용 가능한 문서 링크

| 문서 유형 | URL | 설명 |
|----------|-----|------|
| **Swagger UI** | `http://localhost:8000/docs-static/swagger-ui.html` | 인터랙티브 API 문서 |
| **OpenAPI YAML** | `http://localhost:8000/docs-static/swagger.yaml` | API 스펙 원본 파일 |
| **FastAPI 기본 문서** | `http://localhost:8000/docs` | 개발 모드에서만 활성화 |

### 3. 루트 엔드포인트에서 확인

```bash
curl http://localhost:8000/

# 응답 예시:
{
  "service": "LLM-Lite Underwriter API",
  "version": "1.0.0",
  "status": "running",
  "docs_url": "/docs",
  "swagger_docs": "/docs-static/swagger-ui.html",
  "api_spec": "/docs-static/swagger.yaml",
  "timestamp": "2025-01-21T14:30:52.123456Z"
}
```

## 🎯 Swagger UI 사용법

### 1. API 엔드포인트 탐색

- **태그별 구분**: Health Check, Underwriter, Tasks, Notifications
- **HTTP 메서드별 색상**: GET(초록), POST(파랑), DELETE(빨강)
- **확장/축소**: 각 엔드포인트를 클릭하여 상세 정보 확인

### 2. Try It Out 기능 사용

1. **"Try it out" 버튼 클릭**
2. **요청 파라미터 입력**
3. **"Execute" 버튼 클릭**
4. **응답 결과 확인**

### 3. 주요 테스트 시나리오

#### 시나리오 1: 인수심사 요청 → 상태 확인
```markdown
1. POST /underwrite 실행
   - request_id: "test_001"
   - user_input: "태풍 보험상품 설계해주세요"
   - callback.type: "file_system"

2. 응답에서 task_id 복사

3. GET /tasks/{task_id} 실행
   - path parameter에 task_id 입력

4. 상태가 "completed"가 될 때까지 반복 조회
```

#### 시나리오 2: Webhook 테스트
```markdown
1. POST /notifications/test-webhook 실행
   - url: "https://httpbin.org/post"
   - headers: {"Content-Type": "application/json"}

2. 응답 확인하여 연결 상태 검증
```

## 📝 주요 입출력 예시

### 1. 인수심사 요청 (POST /underwrite)

**입력:**
```json
{
  "request_id": "typhoon_001",
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

**출력:**
```json
{
  "task_id": "underwriter_20250121_143052_a1b2c3d4",
  "request_id": "typhoon_001",
  "status": "accepted",
  "estimated_duration_seconds": 90,
  "created_at": "2025-01-21T14:30:52.123456Z",
  "status_url": "/api/v1/tasks/underwriter_20250121_143052_a1b2c3d4"
}
```

### 2. 작업 상태 조회 (GET /tasks/{task_id})

**출력 (완료된 경우):**
```json
{
  "task_id": "underwriter_20250121_143052_a1b2c3d4",
  "request_id": "typhoon_001",
  "status": "completed",
  "priority": "high",
  "created_at": "2025-01-21T14:30:52.123456Z",
  "started_at": "2025-01-21T14:30:55.789012Z",
  "completed_at": "2025-01-21T14:32:15.654321Z",
  "processing_duration": 83.5,
  "progress": {
    "percentage": 100.0,
    "current_step": "completed",
    "completed_steps": [
      "peril_canvas",
      "prior_extraction", 
      "scenario_generation",
      "pricing_calculation",
      "pricing_report"
    ],
    "total_steps": 5
  },
  "result": {
    "status": "success",
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
  "callback_status": "success"
}
```

## 🔧 고급 사용법

### 1. curl을 통한 API 호출

Swagger UI의 "Copy as cURL" 기능을 사용하여 명령행에서 테스트:

```bash
# 인수심사 요청
curl -X 'POST' \
  'http://localhost:8000/api/v1/underwrite' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "request_id": "test_001",
  "user_input": "지진 보험상품 설계",
  "callback": {"type": "file_system"},
  "options": {"simulation_years": 1000}
}'
```

### 2. 다른 프로그래밍 언어에서 사용

Swagger UI의 코드 생성 기능을 활용하여 Python, JavaScript, Java 등의 클라이언트 코드 생성 가능.

### 3. Postman 연동

1. Swagger YAML 파일을 Postman에 import
2. 자동으로 API 컬렉션 생성
3. 환경 변수 설정하여 다양한 환경에서 테스트

## 🚨 주의사항

### 1. 실제 API 호출

- Swagger UI의 "Try it out"은 **실제 API를 호출**합니다
- 테스트 데이터를 사용하여 실제 처리가 발생할 수 있습니다
- 프로덕션 환경에서는 주의해서 사용하세요

### 2. 인증 설정

API 키가 필요한 경우:
```markdown
1. Swagger UI 상단의 "Authorize" 버튼 클릭
2. API Key 입력
3. 모든 요청에 자동으로 인증 헤더 추가
```

### 3. 서버 URL 변경

기본적으로 `localhost:8000`으로 설정되어 있습니다. 다른 서버에서 테스트하려면:

1. Swagger UI 상단의 서버 선택 드롭다운 사용
2. 또는 swagger.yaml 파일의 servers 섹션 수정

## 📚 추가 리소스

- **API 사용 가이드**: [api-usage-guide.md](./api-usage-guide.md)
- **OpenAPI 3.0 스펙**: https://swagger.io/specification/
- **Swagger UI 사용법**: https://swagger.io/tools/swagger-ui/

---

💡 **팁**: Swagger UI를 브라우저 북마크에 추가하여 개발 중 빠르게 API를 테스트하세요!