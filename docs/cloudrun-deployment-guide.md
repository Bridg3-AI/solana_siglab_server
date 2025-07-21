# Google Cloud Run 배포 가이드

LLM-Lite Underwriter API를 Google Cloud Run에 배포하는 방법을 안내합니다.

## 📋 사전 준비사항

### 1. Google Cloud SDK 설치
```bash
# macOS
brew install google-cloud-sdk

# Ubuntu/Debian
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 로그인 및 초기화
gcloud auth login
gcloud init
```

### 2. 프로젝트 설정
```bash
# 프로젝트 생성 (선택사항)
gcloud projects create llm-lite-underwriter --name="LLM-Lite Underwriter"

# 프로젝트 설정
gcloud config set project llm-lite-underwriter

# 결제 계정 연결 (필수)
gcloud billing projects link llm-lite-underwriter --billing-account=YOUR_BILLING_ACCOUNT_ID
```

## 🚀 배포 방법

### 방법 1: 자동 배포 스크립트 사용 (권장)

```bash
# 환경 변수 설정
cp .env.cloudrun.example .env.cloudrun
# .env.cloudrun 파일 편집하여 실제 값 입력

# 배포 실행
./deploy-cloudrun.sh
```

### 방법 2: 수동 배포

```bash
# 1. 필요한 API 활성화
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 2. 이미지 빌드
gcloud builds submit --tag gcr.io/PROJECT_ID/underwriter-api .

# 3. Cloud Run 배포
gcloud run deploy underwriter-api \
    --image gcr.io/PROJECT_ID/underwriter-api \
    --platform managed \
    --region asia-northeast1 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 100 \
    --env-vars-file .env.cloudrun
```

### 방법 3: YAML 파일 사용

```bash
# cloudrun.yaml 파일 수정 (PROJECT_ID 교체)
sed -i 's/PROJECT_ID/your-actual-project-id/g' cloudrun.yaml

# 배포
gcloud run services replace cloudrun.yaml --region asia-northeast1
```

## ⚙️ 환경 변수 설정

`.env.cloudrun` 파일에서 다음 중요한 설정을 확인하세요:

```bash
# 필수 설정
OPENAI_API_KEY=your-openai-api-key
API_CORS_ORIGINS=https://your-frontend-domain.com

# 성능 튜닝
API_MAX_CONCURRENT_TASKS=5
API_TASK_TIMEOUT=300

# 보안 설정 (선택사항)
API_VALID_KEYS=key1,key2,key3
```

## 📊 리소스 최적화

### CPU 및 메모리 설정
```yaml
# 기본 설정 (소규모)
cpu: "1000m"      # 1 vCPU
memory: "2Gi"     # 2GB RAM

# 고성능 설정 (대규모)
cpu: "4000m"      # 4 vCPU
memory: "8Gi"     # 8GB RAM
```

### 자동 스케일링
```bash
# 최소/최대 인스턴스 수 설정
gcloud run services update underwriter-api \
    --min-instances 0 \
    --max-instances 100 \
    --region asia-northeast1
```

## 🔒 보안 설정

### 1. IAM 권한
```bash
# 서비스 계정 생성
gcloud iam service-accounts create cloud-run-sa

# 필요한 권한 부여
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:cloud-run-sa@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

### 2. VPC 커넥터 (선택사항)
```bash
# VPC 커넥터 생성 (내부 리소스 접근 시)
gcloud compute networks vpc-access connectors create underwriter-connector \
    --region asia-northeast1 \
    --subnet default \
    --subnet-project PROJECT_ID \
    --range 10.8.0.0/28
```

## 🔍 모니터링 및 로깅

### 1. 로그 확인
```bash
# 실시간 로그 확인
gcloud run logs tail underwriter-api --region asia-northeast1

# 과거 로그 조회
gcloud run logs read underwriter-api --region asia-northeast1 --limit=50
```

### 2. 메트릭스 확인
```bash
# 서비스 상태 확인
gcloud run services describe underwriter-api --region asia-northeast1

# 리비전 목록
gcloud run revisions list --service underwriter-api --region asia-northeast1
```

## 🚨 트러블슈팅

### 일반적인 문제들

1. **메모리 부족**
```bash
# 메모리 증가
gcloud run services update underwriter-api \
    --memory 4Gi \
    --region asia-northeast1
```

2. **타임아웃 에러**
```bash
# 타임아웃 증가
gcloud run services update underwriter-api \
    --timeout 900 \
    --region asia-northeast1
```

3. **Cold Start 지연**
```bash
# 최소 인스턴스 설정
gcloud run services update underwriter-api \
    --min-instances 1 \
    --region asia-northeast1
```

### 디버깅 명령어
```bash
# 서비스 상세 정보
gcloud run services describe underwriter-api --region asia-northeast1

# 최근 배포 로그
gcloud builds log $(gcloud builds list --limit=1 --format="value(id)")

# 헬스 체크
curl -f https://your-service-url/api/v1/health
```

## 💰 비용 최적화

### 1. 리전 선택
- **asia-northeast1** (서울): 낮은 지연시간
- **us-central1** (아이오와): 저렴한 비용

### 2. 자동 스케일링 설정
```bash
# 비용 절약을 위한 설정
--min-instances 0          # 트래픽 없을 때 0으로 스케일다운
--max-instances 10         # 최대 인스턴스 제한
--concurrency 80          # 인스턴스당 동시 요청 수 증가
```

### 3. 리소스 모니터링
```bash
# 사용량 확인
gcloud billing accounts list
gcloud billing projects describe PROJECT_ID
```

## 🔄 CI/CD 파이프라인

### GitHub Actions 설정 예시
```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - uses: google-github-actions/setup-gcloud@v0
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: llm-lite-underwriter
    
    - run: |
        gcloud builds submit --tag gcr.io/llm-lite-underwriter/underwriter-api
        gcloud run deploy underwriter-api \
          --image gcr.io/llm-lite-underwriter/underwriter-api \
          --region asia-northeast1 \
          --allow-unauthenticated
```

## 📞 지원

문제가 발생하면:
1. 로그 확인: `gcloud run logs tail underwriter-api --region asia-northeast1`
2. 서비스 상태: `gcloud run services describe underwriter-api --region asia-northeast1`
3. GitHub Issues에 문의

---

🎯 **배포 완료 후 확인사항**
- [ ] 헬스 체크 정상 동작
- [ ] Swagger UI 접근 가능
- [ ] 실제 API 요청 테스트
- [ ] 모니터링 및 알림 설정