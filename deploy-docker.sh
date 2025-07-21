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

echo "✅ Deployed using Docker image (not buildpacks)"