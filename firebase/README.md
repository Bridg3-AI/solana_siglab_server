# Firebase Module

이 디렉토리는 Solana SigLab Server의 모든 Firebase 관련 기능을 포함합니다.

## 📁 구조

```
firebase/
├── __init__.py              # 메인 Firebase 모듈 (전역 exports)
├── core/                    # 핵심 Firebase 기능
│   ├── __init__.py
│   ├── firebase_init.py     # Firebase 앱 초기화 (싱글톤)
│   ├── exceptions.py        # Firebase 관련 예외
│   └── logging.py          # 구조화된 로깅
├── auth/                    # 인증 관련
│   ├── __init__.py
│   └── middleware.py       # 인증 미들웨어
├── database/               # Firestore 데이터베이스
│   ├── __init__.py
│   └── services.py         # Firestore 서비스 클래스
├── storage/               # Firebase Storage
│   ├── __init__.py
│   └── services.py        # Storage 서비스 클래스
├── rules/                 # 보안 규칙
│   ├── __init__.py
│   ├── firestore.rules    # Firestore 보안 규칙
│   └── storage.rules      # Storage 보안 규칙
├── config/               # 설정 파일
│   ├── __init__.py
│   ├── firebase.json     # Firebase 프로젝트 설정
│   ├── .firebaserc       # 프로젝트 별칭
│   └── firestore.indexes.json  # Firestore 인덱스
└── README.md            # 이 파일
```

## 🚀 사용법

### 기본 Firebase 기능

```python
# Firebase 앱 및 클라이언트 가져오기
from firebase import get_db, get_storage, firebase_app

# Firestore 사용
db = get_db()
doc_ref = db.collection('users').document('user123')

# Storage 사용
storage = get_storage()
```

### 인증

```python
from firebase import AuthMiddleware

# 토큰 검증
user_info = AuthMiddleware.verify_token(token)

# 데코레이터로 엔드포인트 보호
@require_auth
def protected_function(req):
    user = req.user  # 자동으로 추가됨
    pass
```

### 로깅

```python
from firebase.core.logging import logger, log_agent_interaction

# 구조화된 로깅
logger.info("Operation completed", user_id="123", operation="balance_check")

# 에이전트 상호작용 로깅
log_agent_interaction(
    session_id="sess123",
    user_input="Check balance",
    agent_response="Balance: 1.5 SOL",
    tools_used=["get_balance"],
    iterations=1
)
```

### 데이터베이스 서비스

```python
from firebase.database import FirestoreService

# 고급 Firestore 작업
firestore_service = FirestoreService(get_db())

# 문서 생성
user_id = firestore_service.create_document("users", data={
    "username": "john_doe",
    "email": "john@example.com"
})

# 쿼리
users = firestore_service.query_collection(
    "users", 
    filters=[("username", "==", "john_doe")],
    limit=10
)

# 배치 작업
operations = [
    {"type": "create", "collection": "logs", "document_id": "log1", "data": {"event": "login"}},
    {"type": "update", "collection": "users", "document_id": "user123", "data": {"last_seen": "now"}}
]
firestore_service.batch_write(operations)
```

### Storage 서비스

```python
from firebase.storage import StorageService

# Storage 작업
storage_service = StorageService()

# 파일 업로드
public_url = storage_service.upload_file(
    local_path="/tmp/profile.jpg",
    storage_path="users/user123/profile.jpg",
    metadata={"owner": "user123"}
)

# 문자열 업로드
url = storage_service.upload_from_string(
    content="Hello World",
    storage_path="exports/data.txt",
    content_type="text/plain"
)

# 파일 메타데이터
metadata = storage_service.get_file_metadata("users/user123/profile.jpg")

# 임시 액세스 URL 생성
signed_url = storage_service.generate_signed_url(
    "private/document.pdf",
    expiration_minutes=60
)
```

## 🔧 설정

### 환경 변수

Firebase 관련 환경 변수들은 `firebase.json`에서 설정:

```json
{
  "functions": [{
    "environmentVariables": {
      "SOLANA_NETWORK": "mainnet-beta",
      "MAX_ITERATIONS": "10",
      "DEBUG_MODE": "false"
    }
  }]
}
```

### 멀티 환경

`.firebaserc`를 통한 환경별 프로젝트 관리:

```json
{
  "projects": {
    "default": "solana-siglab",
    "development": "solana-siglab-dev",
    "staging": "solana-siglab-staging",
    "production": "solana-siglab"
  }
}
```

## 🛡️ 보안

### Firestore 규칙

`rules/firestore.rules`에서 관리:

```javascript
// 사용자는 자신의 데이터만 액세스
match /users/{userId} {
  allow read, write: if isOwner(userId) || isAdmin();
}

// 대화는 인증된 사용자만
match /conversations/{sessionId} {
  allow read, write: if isAuthenticated();
}
```

### Storage 규칙

`rules/storage.rules`에서 관리:

```javascript
// 프로필 이미지 (5MB 제한)
match /users/{userId}/profile/{allPaths=**} {
  allow write: if request.auth.uid == userId
               && request.resource.size <= 5 * 1024 * 1024
               && request.resource.contentType.matches('image/.*');
}
```

## 📊 모니터링

### 성능 모니터링

```python
from firebase.core.logging import log_performance

# 성능 측정
log_performance("database_query", duration_ms=150, query_type="user_lookup")
```

### 에러 추적

```python
from firebase.core.logging import log_error

try:
    risky_operation()
except Exception as e:
    log_error(e, context="user_creation", user_id="123")
    raise
```

## 🚀 배포

Firebase 관련 모든 설정은 루트의 `firebase.json`에서 참조:

```bash
# 규칙만 배포
firebase deploy --only firestore:rules,storage

# 전체 배포
./scripts/deploy.sh production
```

## 🔮 확장성

이 구조는 다음과 같은 확장을 지원합니다:

- **새로운 서비스**: `firebase/new_service/` 추가
- **커스텀 인증**: `firebase/auth/` 확장
- **고급 Storage**: `firebase/storage/` 기능 추가
- **실시간 기능**: Realtime Database, Messaging 등

## 📚 참고 자료

- [Firebase 2025 Integration Guide](../docs/firebase-2025-integration.md)
- [API Documentation](../docs/api.md)
- [Architecture Overview](../docs/architecture.md)