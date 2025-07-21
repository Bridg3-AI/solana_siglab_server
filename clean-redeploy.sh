#!/bin/bash

echo "🧹 완전한 재배포로 revision 충돌 해결..."

SERVICE_NAME="solana-siglab-server"
REGION="asia-northeast3"
PROJECT_ID="siglab-solana"

# 1. 기존 서비스 완전 삭제 (주의: 프로덕션에서는 사용 금지)
echo "⚠️ 기존 서비스 삭제 중..."
gcloud run services delete $SERVICE_NAME --region=$REGION --quiet || echo "서비스가 이미 삭제되었거나 존재하지 않음"

# 2. 잠시 대기
sleep 5

# 3. Procfile이 있는지 확인
if [ ! -f "Procfile" ]; then
    echo "❌ Procfile이 없습니다!"
    exit 1
fi

echo "✅ Procfile 내용:"
cat Procfile

# 4. 새로 배포 (buildpack 사용)
echo "🚀 새로 배포 시작..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region=$REGION \
  --update-secrets "OPENAI_API_KEY=openai-api-key:latest" \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=900s \
  --port=8080 \
  --max-instances=10

# 5. 배포 상태 확인
echo "📊 배포 결과 확인:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="table(status.url,status.traffic[].revisionName,status.traffic[].percent)"

echo "✅ 완전 재배포 완료!"