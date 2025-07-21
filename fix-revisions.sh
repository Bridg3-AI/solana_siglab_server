#!/bin/bash

echo "🔧 Cloud Run revision 문제 해결 중..."

SERVICE_NAME="solana-siglab-server"
REGION="asia-northeast3"

# 1. 현재 revision 상태 확인
echo "📋 현재 revision 상태:"
gcloud run revisions list --service=$SERVICE_NAME --region=$REGION

# 2. 모든 트래픽을 최신 revision으로 라우팅
echo "🚦 모든 트래픽을 최신 revision으로 라우팅..."
gcloud run services update-traffic $SERVICE_NAME \
  --to-latest \
  --region=$REGION

# 3. 구 revision 정리 (최신 것만 유지)
echo "🗑️ 구 revision 정리 중..."
gcloud run revisions list --service=$SERVICE_NAME --region=$REGION --format="value(REVISION)" --limit=10 | tail -n +2 | while read revision; do
  if [ ! -z "$revision" ]; then
    echo "삭제 중: $revision"
    gcloud run revisions delete $revision --region=$REGION --quiet || echo "⚠️ $revision 삭제 실패 (사용 중일 수 있음)"
  fi
done

# 4. 서비스 상태 확인
echo "✅ 최종 상태 확인:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="table(status.traffic[].revisionName,status.traffic[].percent)"

echo "🎉 revision 정리 완료!"