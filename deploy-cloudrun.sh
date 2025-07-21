#!/bin/bash
# =============================================================================
# Google Cloud Run 배포 스크립트
# LLM-Lite Underwriter API
# =============================================================================

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정 변수
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-llm-lite-underwriter}"
SERVICE_NAME="${SERVICE_NAME:-underwriter-api}"
REGION="${REGION:-asia-northeast1}"  # 서울 리전
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
PORT=8080

echo -e "${BLUE}🚀 LLM-Lite Underwriter API - Google Cloud Run 배포 시작${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "프로젝트 ID: ${GREEN}${PROJECT_ID}${NC}"
echo -e "서비스명: ${GREEN}${SERVICE_NAME}${NC}"
echo -e "리전: ${GREEN}${REGION}${NC}"
echo -e "이미지: ${GREEN}${IMAGE_NAME}${NC}"
echo ""

# 1. 프로젝트 설정 확인
echo -e "${YELLOW}📋 1. Google Cloud 프로젝트 설정 확인...${NC}"
if ! gcloud config get-value project &>/dev/null; then
    echo -e "${RED}❌ Google Cloud 프로젝트가 설정되지 않았습니다.${NC}"
    echo "다음 명령으로 프로젝트를 설정하세요:"
    echo "gcloud config set project ${PROJECT_ID}"
    exit 1
fi

CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
echo -e "현재 프로젝트: ${GREEN}${CURRENT_PROJECT}${NC}"

# 2. 필요한 API 활성화
echo -e "${YELLOW}🔧 2. 필요한 Google Cloud API 활성화...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 3. Docker 이미지 빌드
echo -e "${YELLOW}🐳 3. Docker 이미지 빌드...${NC}"
echo "이미지 빌드 중: ${IMAGE_NAME}:latest"

# Cloud Build를 사용한 이미지 빌드 (로컬 Docker 불필요)
gcloud builds submit --tag ${IMAGE_NAME}:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker 이미지 빌드 실패${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker 이미지 빌드 완료${NC}"

# 4. Cloud Run에 배포
echo -e "${YELLOW}☁️  4. Cloud Run에 서비스 배포...${NC}"

# 환경 변수 파일이 있는지 확인
ENV_FILE=".env.cloudrun"
ENV_VARS_OPTION=""

if [ -f "${ENV_FILE}" ]; then
    echo -e "환경 변수 파일 발견: ${GREEN}${ENV_FILE}${NC}"
    ENV_VARS_OPTION="--env-vars-file=${ENV_FILE}"
else
    echo -e "${YELLOW}⚠️  환경 변수 파일이 없습니다. 기본 설정으로 배포합니다.${NC}"
    echo "프로덕션 배포를 위해서는 .env.cloudrun 파일을 생성하세요."
fi

# Cloud Run 배포 실행
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --port ${PORT} \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 100 \
    --concurrency 80 \
    ${ENV_VARS_OPTION}

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Cloud Run 배포 실패${NC}"
    exit 1
fi

# 5. 배포 완료 정보 출력
echo -e "${GREEN}🎉 배포 완료!${NC}"
echo -e "${BLUE}================================================${NC}"

# 서비스 URL 가져오기
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')

echo -e "서비스 URL: ${GREEN}${SERVICE_URL}${NC}"
echo -e "API 문서: ${GREEN}${SERVICE_URL}/docs-static/swagger-ui.html${NC}"
echo -e "헬스 체크: ${GREEN}${SERVICE_URL}/api/v1/health${NC}"

# 6. 배포 상태 확인
echo -e "${YELLOW}🔍 배포 상태 확인 중...${NC}"
sleep 5

# 헬스 체크 실행
if command -v curl >/dev/null 2>&1; then
    echo "헬스 체크 요청 전송 중..."
    
    if curl -f -s "${SERVICE_URL}/api/v1/health" >/dev/null; then
        echo -e "${GREEN}✅ 헬스 체크 성공! 서비스가 정상적으로 실행 중입니다.${NC}"
    else
        echo -e "${YELLOW}⚠️  헬스 체크 실패. 서비스가 아직 준비되지 않았을 수 있습니다.${NC}"
        echo "몇 분 후 다시 확인해보세요: ${SERVICE_URL}/api/v1/health"
    fi
else
    echo -e "${YELLOW}⚠️  curl이 설치되지 않아 헬스 체크를 건너뜁니다.${NC}"
fi

echo ""
echo -e "${BLUE}📊 추가 관리 명령어:${NC}"
echo "로그 확인: gcloud run logs read ${SERVICE_NAME} --region ${REGION}"
echo "서비스 상태: gcloud run services describe ${SERVICE_NAME} --region ${REGION}"
echo "트래픽 분할: gcloud run services update-traffic ${SERVICE_NAME} --to-latest --region ${REGION}"

echo ""
echo -e "${GREEN}🎯 배포 스크립트 완료!${NC}"