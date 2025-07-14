# Solana SigLab Server

LangGraph 에이전트를 활용한 Solana 블록체인 상호작용 Firebase 백엔드 서버

## 프로젝트 구조

```
solana_siglab_server/
├── src/                      # 소스 코드 (계층형 아키텍처)
│   ├── api/                  # Firebase Functions API 엔드포인트
│   │   └── main.py          # 메인 API 함수들
│   ├── services/            # 비즈니스 로직 레이어
│   │   ├── solana_service.py # Solana/에이전트 작업
│   │   └── user_service.py   # 사용자 관리
│   ├── models/              # 데이터 모델 (Pydantic)
│   │   ├── agent.py         # 에이전트 요청/응답 모델
│   │   └── user.py          # 사용자 데이터 모델
│   ├── utils/               # 유틸리티 함수
│   │   ├── decorators.py    # 성능 모니터링, 에러 처리
│   │   ├── response.py      # API 응답 빌더
│   │   └── validation.py    # 입력 검증
│   ├── config/              # 애플리케이션 설정
│   │   └── settings.py      # 설정 관리
│   └── requirements.txt     # Python 의존성
├── firebase/                # Firebase 모듈 (분리됨)
│   ├── core/               # 핵심 Firebase 기능
│   │   ├── firebase_init.py # Firebase 앱 초기화 (싱글톤)
│   │   ├── exceptions.py    # 커스텀 예외
│   │   └── logging.py      # 구조화된 로깅
│   ├── auth/               # 인증 관련
│   │   └── middleware.py   # JWT 인증 미들웨어
│   ├── database/           # Firestore 데이터베이스
│   │   └── services.py     # 고급 Firestore 서비스
│   ├── storage/            # Firebase Storage
│   │   └── services.py     # 파일 업로드/다운로드 서비스
│   ├── rules/              # 보안 규칙
│   │   ├── firestore.rules # Firestore 보안 규칙
│   │   └── storage.rules   # Storage 보안 규칙
│   └── config/            # Firebase 설정
│       ├── firebase.json  # Firebase 프로젝트 설정
│       ├── .firebaserc    # 프로젝트 별칭
│       └── firestore.indexes.json # Firestore 인덱스
├── agents/                 # LangGraph AI 에이전트
│   ├── agent.py           # 메인 에이전트 구현
│   ├── memory.py          # 대화 메모리 관리
│   ├── langgraph.json     # LangGraph 설정
│   └── utils/             # 에이전트 유틸리티
│       ├── state.py       # 상태 정의
│       ├── tools.py       # Solana 도구들
│       └── nodes.py       # 그래프 노드 함수들
├── config/                # 빌드 설정
│   ├── package.json      # Node.js 의존성
│   └── package-lock.json # 잠금 파일
├── docs/                  # 문서
│   ├── README.md         # 이 파일
│   ├── api.md            # API 문서
│   ├── architecture.md   # 아키텍처 문서
│   └── firebase-2025-integration.md # Firebase 통합 가이드
├── scripts/              # 유틸리티 스크립트
│   └── deploy.sh         # 자동화된 배포 스크립트
├── tests/                # 테스트 파일
├── firebase.json         # Firebase CLI 설정 (루트 필수)
├── .firebaserc          # Firebase 프로젝트 별칭 (루트 필수)
└── package.json         # NPM 의존성 (루트)
```

## 설치 및 설정

1. Node.js 의존성 설치:
```bash
npm install
```

2. Python 의존성 설치 (Functions):
```bash
cd src
pip install -r requirements.txt
```

3. 에이전트 의존성 설치:
```bash
cd agents
pip install -r requirements.txt
```

4. 환경 설정:
```bash
# 에이전트 환경 변수 설정
cp agents/.env.example agents/.env
# agents/.env 파일을 편집하여 설정값 입력

# Firebase 프로젝트 설정
firebase login
firebase use your-project-id
```

5. 개발 서버 시작:
```bash
# Firebase 에뮬레이터 시작
npm run serve

# 또는 자동화된 배포 스크립트 사용
./scripts/deploy.sh development
```

## API 엔드포인트

### 핵심 엔드포인트
- `GET /hello_world` - 기본 헬로 엔드포인트 (시스템 상태 포함)
- `GET /health_check` - 건강 상태 체크 (서비스 가용성 포함)
- `GET /api_users` - Firestore에서 사용자 목록 조회
- `POST /api_users` - 새 사용자 생성

### 에이전트 엔드포인트
- `POST /solana_agent` - Solana 블록체인 에이전트 상호작용
- `GET /conversation_history` - 세션별 대화 기록 조회

### 에이전트 요청 예시
```bash
curl -X POST https://your-function-url/solana_agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "11111111111111111111111111111112 주소의 잔액을 확인해주세요",
    "session_id": "user123",
    "network": "mainnet-beta"
  }'
```

### 응답 예시
```json
{
  "response": "주소 11111111111111111111111111111112의 잔액: 0.000000000 SOL",
  "context": {},
  "tools_used": ["get_solana_balance"],
  "iterations": 1,
  "intent": "check_balance",
  "session_id": "user123"
}
```

## 에이전트 기능

- **잔액 조회**: 모든 Solana 주소의 SOL 잔액 확인
- **거래 정보**: 서명으로 거래 세부사항 조회
- **서명 검증**: 블록체인상 서명 존재 여부 확인
- **계정 정보**: 상세한 계정 데이터 조회
- **대화 메모리**: Firestore의 지속적인 대화 기록
- **의도 인식**: 사용자 요청의 자동 분류

## Firebase 2025 기능

- **Cloud Functions**: 에이전트 통합 Python 기반 서버리스 함수
- **Firestore**: 대화 저장소를 포함한 NoSQL 데이터베이스
- **보안 규칙**: 사용자 및 대화에 대한 적절한 접근 제어
- **Storage**: 파일 업로드 및 관리
- **에뮬레이터 도구**: 로컬 개발 환경
- **모니터링**: 구조화된 로깅 및 성능 추적
- **인증**: JWT 토큰 기반 사용자 인증

## 에이전트 아키텍처

에이전트는 LangGraph의 Think-Act-Observe 패턴을 사용합니다:

1. **Think (사고)**: 사용자 입력을 분석하고 의도를 파악
2. **Act (행동)**: 적절한 Solana 블록체인 도구 실행
3. **Observe (관찰)**: 결과를 평가하고 다음 단계 결정

지원되는 의도:
- `check_balance`: 잔액 조회
- `transaction_info`: 거래 세부사항
- `verify_signature`: 서명 검증
- `account_info`: 계정 정보
- `general_query`: 일반 질문

## Firebase 2025 최적화

### Cold Start 최적화
- 싱글톤 패턴을 통한 Firebase 앱 초기화
- 전역 서비스 인스턴스 캐싱
- 메모리 최적화 (512MB)
- 동시성 처리 (인스턴스당 10개 요청)

### 보안 강화
- 고급 Firestore 보안 규칙 (헬퍼 함수 포함)
- Storage 보안 규칙 (파일 크기/타입 제한)
- JWT 인증 미들웨어
- 입력 검증 및 정제

### 모니터링 및 로깅
- 구조화된 JSON 로깅 (Firebase Cloud Logging 최적화)
- 성능 모니터링 데코레이터
- 에러 추적 및 상세 예외 정보
- 에이전트 상호작용 로깅

## 배포

### 자동화된 배포 스크립트
```bash
# 개발 환경 배포
./scripts/deploy.sh development

# 스테이징 환경 배포  
./scripts/deploy.sh staging

# 프로덕션 배포
./scripts/deploy.sh production
```

### 수동 배포
```bash
# 모든 함수 배포
npm run deploy

# 특정 함수만 배포
firebase deploy --only functions:solana_agent

# Firestore 규칙만 배포
firebase deploy --only firestore:rules

# Storage 규칙만 배포
firebase deploy --only storage
```

## 개발

### 로컬 개발
```bash
# 모든 에뮬레이터 시작
npm run serve

# 함수 로그 확인
npm run logs

# 대화형 셸
npm run shell

# 에이전트 로컬 테스트
cd agents
python -c "from agents import run_solana_agent; print(run_solana_agent('help'))"
```

### Firebase 모듈 사용
```python
# Firebase 기능 사용
from firebase import get_db, AuthMiddleware
from firebase.database import FirestoreService
from firebase.core.logging import logger

# 고급 데이터베이스 작업
db_service = FirestoreService(get_db())
users = db_service.query_collection('users', 
    filters=[('active', '==', True)], 
    limit=10)

# 구조화된 로깅
logger.info("Operation completed", user_id="123", operation="balance_check")
```

## 환경 변수

### 에이전트 설정 (`agents/.env`)
```env
SOLANA_NETWORK=mainnet-beta
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
MAX_ITERATIONS=10
DEBUG_MODE=false
ENABLE_MEMORY=true
MEMORY_TYPE=firestore
```

### Firebase 설정 (`firebase.json`)
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

## 프로젝트 특징

### 🏗️ 아키텍처 장점
- **계층형 구조**: API, 서비스, 모델 레이어 분리
- **모듈화**: Firebase 기능이 별도 모듈로 구성
- **확장성**: 새로운 서비스 및 에이전트 쉽게 추가 가능
- **테스트 용이성**: 각 레이어가 독립적으로 테스트 가능

### 🚀 성능 최적화
- Cold Start 최소화 (싱글톤 패턴)
- 메모리 및 동시성 최적화
- 효율적인 데이터베이스 쿼리
- 캐싱 전략 적용

### 🛡️ 보안 모범 사례
- 입력 검증 및 정제
- JWT 기반 인증
- 세밀한 Firestore 보안 규칙
- 파일 업로드 제한 및 검증

### 📊 모니터링 및 관찰성
- 구조화된 로깅
- 성능 메트릭 수집
- 에러 추적 및 알림
- 에이전트 상호작용 분석
