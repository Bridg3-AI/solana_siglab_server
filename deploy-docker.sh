#!/bin/bash

# Force Docker buildpack usage for Cloud Run deployment
# This prevents Google's buildpacks from auto-detecting gunicorn

echo "🐳 Deploying with Docker (not buildpacks)..."

# Method 1: Build image first, then deploy
gcloud builds submit --tag gcr.io/siglab-solana/solana-siglab-server . && \
gcloud run deploy solana-siglab-server \
  --image gcr.io/siglab-solana/solana-siglab-server \
  --region asia-northeast3 \
  --update-secrets "OPENAI_API_KEY=openai-api-key:latest" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900s

# 모든 트래픽을 새 revision으로 즉시 라우팅
echo "🚦 트래픽을 새 revision으로 라우팅..."
gcloud run services update-traffic solana-siglab-server \
  --to-latest \
  --region asia-northeast3

echo "✅ Deployed using Docker image (not buildpacks)"