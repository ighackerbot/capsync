#!/bin/bash

# Capsync - Google Cloud Platform Deployment Script
# This script automates deployment to GCP Cloud Run

set -e

echo "🚀 Capsync GCP Deployment Script"
echo "================================"

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"capsync-prod"}
REGION=${GCP_REGION:-"us-central1"}
BACKEND_SERVICE="capsync-backend"
FRONTEND_SERVICE="capsync-frontend"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found!${NC}"
    echo "Please install: brew install --cask google-cloud-sdk"
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI found${NC}"

# Set project
echo -e "${BLUE}🔧 Setting active project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${BLUE}🔌 Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com

# Deploy Backend
echo -e "${BLUE}🔨 Deploying backend to Cloud Run...${NC}"
gcloud run deploy $BACKEND_SERVICE \
  --source backend/api \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars WHISPER_MODEL=small,WHISPER_COMPUTE=int8 \
  --quiet

# Get backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)')
echo -e "${GREEN}✅ Backend deployed: $BACKEND_URL${NC}"

# Deploy Frontend
echo -e "${BLUE}🎨 Building frontend...${NC}"
cd frontend
export VITE_API_BASE=$BACKEND_URL
npm install
npm run build
cd ..

echo -e "${BLUE}🔨 Deploying frontend to Cloud Run...${NC}"
gcloud run deploy $FRONTEND_SERVICE \
  --source frontend \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars VITE_API_BASE=$BACKEND_URL \
  --quiet

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format 'value(status.url)')

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "📱 ${BLUE}Frontend:${NC} $FRONTEND_URL"
echo -e "🔌 ${BLUE}Backend:${NC}  $BACKEND_URL"
echo -e "📚 ${BLUE}API Docs:${NC} $BACKEND_URL/docs"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Test your app: $FRONTEND_URL"
echo "  2. View logs: gcloud run logs tail $BACKEND_SERVICE --region $REGION"
echo "  3. Monitor: https://console.cloud.google.com/run"
echo ""
