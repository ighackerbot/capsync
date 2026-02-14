# Google Cloud Platform Deployment Guide

## 🚀 Deploy Capsync to Google Cloud

Complete guide for deploying your full-stack Capsync application to GCP using Cloud Run (recommended), App Engine, or Compute Engine.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Option 1: Cloud Run (Recommended)](#option-1-cloud-run-recommended)
3. [Option 2: App Engine](#option-2-app-engine)
4. [Option 3: Compute Engine (VM)](#option-3-compute-engine-vm)
5. [Cloud Build CI/CD](#cloud-build-cicd)
6. [Cost Estimation](#cost-estimation)

---

## Prerequisites

### 1. Install Google Cloud SDK

**macOS:**
```bash
# Install gcloud CLI
brew install --cask google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

**Verify installation:**
```bash
gcloud version
```

### 2. Initialize gcloud

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  compute.googleapis.com
```

### 3. Create GCP Project

```bash
# Create new project
gcloud projects create capsync-prod --name="Capsync Production"

# Set as active project
gcloud config set project capsync-prod

# Enable billing (required)
# Visit: https://console.cloud.google.com/billing
```

---

## Option 1: Cloud Run (Recommended) ⭐

**Best for**: Containerized apps, auto-scaling, pay-per-use

### Why Cloud Run?
✅ Automatic scaling (0 to N)  
✅ Pay only for actual usage  
✅ Managed infrastructure  
✅ Built-in HTTPS  
✅ Easy rollbacks  
✅ CI/CD integration  

### Quick Deploy

#### Step 1: Deploy Backend

```bash
cd /Users/anujjain/capsync-5

# Build and deploy backend
gcloud run deploy capsync-backend \
  --source backend/api \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars WHISPER_MODEL=small,WHISPER_COMPUTE=int8

# Copy the backend URL (e.g., https://capsync-backend-xxx.run.app)
```

#### Step 2: Deploy Frontend

```bash
# Update frontend environment
cd frontend
export VITE_API_BASE=https://capsync-backend-xxx.run.app

# Build frontend
npm run build

# Deploy frontend
gcloud run deploy capsync-frontend \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

#### Step 3: Access Your App

```
Frontend: https://capsync-frontend-xxx.run.app
Backend:  https://capsync-backend-xxx.run.app
API Docs: https://capsync-backend-xxx.run.app/docs
```

### Using Docker Images (Alternative)

```bash
# Backend
cd /Users/anujjain/capsync-5
docker build -t gcr.io/capsync-prod/backend backend/api
docker push gcr.io/capsync-prod/backend

gcloud run deploy capsync-backend \
  --image gcr.io/capsync-prod/backend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi

# Frontend
docker build -t gcr.io/capsync-prod/frontend \
  --build-arg VITE_API_BASE=https://capsync-backend-xxx.run.app \
  frontend

docker push gcr.io/capsync-prod/frontend

gcloud run deploy capsync-frontend \
  --image gcr.io/capsync-prod/frontend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

---

## Option 2: App Engine

**Best for**: Simpler deployment, managed scaling

### Deploy Backend

```bash
cd /Users/anujjain/capsync-5/backend/api

# Deploy to App Engine
gcloud app deploy app.yaml

# Get URL
gcloud app browse
```

### Deploy Frontend

**Option A: Firebase Hosting (Recommended for frontend)**

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize Firebase
cd /Users/anujjain/capsync-5/frontend
firebase init hosting

# Build
npm run build

# Deploy
firebase deploy --only hosting
```

**Option B: Cloud Storage + Load Balancer**

```bash
cd /Users/anujjain/capsync-5/frontend

# Build frontend
npm run build

# Create bucket
gsutil mb gs://capsync-frontend

# Upload files
gsutil -m cp -r dist/* gs://capsync-frontend

# Make public
gsutil iam ch allUsers:objectViewer gs://capsync-frontend

# Enable website
gsutil web set -m index.html -e index.html gs://capsync-frontend
```

---

## Option 3: Compute Engine (VM)

**Best for**: Full control, heavy workloads

### Create VM Instance

```bash
# Create VM
gcloud compute instances create capsync-vm \
  --zone=us-central1-a \
  --machine-type=e2-standard-2 \
  --boot-disk-size=50GB \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=http-server,https-server

# Allow HTTP/HTTPS
gcloud compute firewall-rules create allow-http \
  --allow tcp:80,tcp:443 \
  --target-tags http-server,https-server
```

### Setup on VM

```bash
# SSH into VM
gcloud compute ssh capsync-vm --zone=us-central1-a

# Install dependencies
sudo apt update
sudo apt install -y python3.11 python3.11-venv nodejs npm nginx certbot python3-certbot-nginx git ffmpeg

# Clone repository
cd /var/www
sudo git clone https://github.com/ighackerbot/capsync.git
cd capsync

# Setup backend
cd backend/api
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/capsync-backend.service
```

**systemd service file:**
```ini
[Unit]
Description=Capsync Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/capsync/backend/api
Environment="WHISPER_MODEL=small"
ExecStart=/var/www/capsync/backend/api/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start backend service
sudo systemctl daemon-reload
sudo systemctl enable capsync-backend
sudo systemctl start capsync-backend

# Setup frontend
cd /var/www/capsync/frontend
npm install
npm run build

# Configure Nginx
sudo nano /etc/nginx/sites-available/capsync
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    # Frontend
    location / {
        root /var/www/capsync/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/capsync /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL (optional)
sudo certbot --nginx -d your-domain.com
```

---

## Cloud Build CI/CD

### Automatic Deployment from GitHub

#### 1. Connect GitHub

```bash
# Connect your repository
gcloud builds submit --config cloudbuild.yaml
```

#### 2. Setup Trigger

```bash
# Create build trigger
gcloud builds triggers create github \
  --name=capsync-deploy \
  --repo-name=capsync \
  --repo-owner=ighackerbot \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml
```

Now every push to `main` triggers automatic deployment! 🎉

---

## Environment Variables

### Cloud Run
```bash
gcloud run services update capsync-backend \
  --set-env-vars WHISPER_MODEL=small,WHISPER_COMPUTE=int8
```

### App Engine
Edit `app.yaml`:
```yaml
env_variables:
  WHISPER_MODEL: "small"
  WHISPER_COMPUTE: "int8"
```

---

## Custom Domain

### Map Custom Domain to Cloud Run

```bash
# Map domain
gcloud run domain-mappings create \
  --service capsync-frontend \
  --domain capsync.yourdomain.com \
  --region us-central1

# Follow DNS instructions
```

### SSL/HTTPS

Cloud Run automatically provisions SSL certificates! ✅

---

## Monitoring & Logs

### View Logs

```bash
# Cloud Run logs
gcloud run logs read capsync-backend --limit 50 --region us-central1

# Follow logs
gcloud run logs tail capsync-backend --region us-central1

# App Engine logs
gcloud app logs tail
```

### Cloud Monitoring

```bash
# Open monitoring dashboard
gcloud monitoring dashboards list
```

Access full monitoring at: https://console.cloud.google.com/monitoring

---

## Cost Estimation

### Cloud Run (Pay-per-use)

**Free Tier (Monthly):**
- 2 million requests
- 360,000 GB-seconds
- 180,000 vCPU-seconds

**Estimated Cost** (after free tier):
- Light usage: $5-10/month
- Medium usage: $20-30/month
- Heavy usage: $50-100/month

### App Engine

**Standard Environment:**
- F1 instance: ~$0.05/hour = ~$37/month
- F4 instance: ~$0.20/hour = ~$146/month

### Compute Engine

**e2-standard-2 (2 vCPUs, 8GB RAM):**
- $48.70/month (us-central1)
- Plus storage: ~$10/month

### Recommendation

Start with **Cloud Run** - only pay for what you use! 💡

---

## Scaling Configuration

### Cloud Run Auto-scaling

```bash
gcloud run services update capsync-backend \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80 \
  --region us-central1
```

### App Engine Scaling

Edit `app.yaml`:
```yaml
automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.65
```

---

## Troubleshooting

### Backend not responding

```bash
# Check logs
gcloud run logs read capsync-backend --region us-central1

# Check service status
gcloud run services describe capsync-backend --region us-central1
```

### Out of memory

```bash
# Increase memory
gcloud run services update capsync-backend \
  --memory 4Gi \
  --region us-central1
```

### Cold start issues

```bash
# Set minimum instances
gcloud run services update capsync-backend \
  --min-instances 1 \
  --region us-central1
```

---

## Complete Deployment Checklist

- [ ] Install Google Cloud SDK
- [ ] Create GCP project
- [ ] Enable required APIs
- [ ] Deploy backend to Cloud Run
- [ ] Deploy frontend to Cloud Run/Firebase
- [ ] Configure environment variables
- [ ] Set up custom domain (optional)
- [ ] Configure Cloud Build trigger
- [ ] Set up monitoring/alerts
- [ ] Test deployment

---

## Quick Command Reference

```bash
# Deploy everything (Cloud Run)
gcloud run deploy capsync-backend --source backend/api --region us-central1
gcloud run deploy capsync-frontend --source frontend --region us-central1

# View services
gcloud run services list

# Delete service
gcloud run services delete capsync-backend --region us-central1

# View logs
gcloud run logs tail capsync-backend --region us-central1

# Update env vars
gcloud run services update capsync-backend \
  --set-env-vars KEY=VALUE \
  --region us-central1
```

---

## Support

- **GCP Documentation**: https://cloud.google.com/docs
- **Cloud Run Docs**: https://cloud.google.com/run/docs
- **GCP Community**: https://cloud.google.com/community

---

## Next Steps

1. **Deploy Now**: Run the Cloud Run commands above
2. **Test**: Upload a video and test captioning
3. **Monitor**: Check logs and metrics
4. **Scale**: Adjust resources as needed
5. **Automate**: Set up Cloud Build triggers

**Your Capsync app will be live on Google Cloud in minutes!** 🚀
