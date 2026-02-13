# Capsync Deployment Guide

## 🚀 Production Deployment Options

This guide covers multiple deployment strategies for Capsync, from simple cloud deployments to custom VPS setups.

---

## Table of Contents

1. [Docker Deployment](#docker-deployment)
2. [Vercel + Railway](#vercel--railway)
3. [Render.com](#rendercom)
4. [AWS/DigitalOcean VPS](#vps-deployment)
5. [Monitoring & Maintenance](#monitoring)

---

## 1. Docker Deployment (Recommended)

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Quick Deploy

```bash
# Clone repository
git clone https://github.com/ighackerbot/capsync.git
cd capsync

# Copy environment file
cp .env.example .env

# Edit environment variables
nano .env

# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f
```

### Configuration

Edit `.env` file:
```bash
WHISPER_MODEL=small          # Options: tiny, base, small, medium, large
WHISPER_COMPUTE=int8         # Compute type
VITE_API_BASE=http://backend:8000  # Backend URL for frontend
```

### Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild after code changes
docker-compose up -d --build

# Scale services
docker-compose up -d --scale backend=3
```

---

## 2. Vercel + Railway

Best for: Quick deployments, serverless architecture

### Frontend (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel --prod
```

**Environment Variables in Vercel:**
- `VITE_API_BASE`: Your Railway backend URL

### Backend (Railway)

1. **Connect GitHub Repository**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your `capsync` repository

2. **Configure Service**
   - Root Directory: `backend/api`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Environment Variables**
   ```
   WHISPER_MODEL=small
   WHISPER_COMPUTE=int8
   PORT=${{PORT}}
   ```

4. **Get URL**
   - Copy the Railway-provided URL
   - Update Vercel's `VITE_API_BASE` with this URL

**Cost**: ~$5-10/month for backend

---

## 3. Render.com

Best for: All-in-one platform, simplified deployment

### Backend Service

1. Create new **Web Service**
2. Configuration:
   ```
   Name: capsync-backend
   Environment: Python 3.11
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   Root Directory: backend/api
   ```

3. Environment Variables:
   ```
   WHISPER_MODEL=small
   WHISPER_COMPUTE=int8
   ```

4. Instance Type: Starter ($7/month)

### Frontend Service

1. Create new **Static Site**
2. Configuration:
   ```
   Name: capsync-frontend
   Build Command: npm install && npm run build
   Publish Directory: dist
   Root Directory: frontend
   ```

3. Environment Variables:
   ```
   VITE_API_BASE=https://capsync-backend.onrender.com
   ```

**Total Cost**: ~$7/month

---

## 4. VPS Deployment (Ubuntu 22.04)

Best for: Full control, custom configurations

### Initial Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv nodejs npm nginx certbot python3-certbot-nginx git ffmpeg

# Clone repository
sudo mkdir -p /var/www
cd /var/www
sudo git clone https://github.com/ighackerbot/capsync.git
cd capsync
```

### Backend Setup

```bash
# Setup Python environment
cd /var/www/capsync/backend/api
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Create Systemd Service:**

```bash
sudo nano /etc/systemd/system/capsync-backend.service
```

```ini
[Unit]
Description=Capsync Backend API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/capsync/backend/api
Environment="WHISPER_MODEL=small"
Environment="WHISPER_COMPUTE=int8"
ExecStart=/var/www/capsync/backend/api/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable capsync-backend
sudo systemctl start capsync-backend
sudo systemctl status capsync-backend
```

### Frontend Setup

```bash
# Build frontend
cd /var/www/capsync/frontend
npm install
npm run build
```

**Configure Nginx:**

```bash
sudo nano /etc/nginx/sites-available/capsync
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Frontend
    location / {
        root /var/www/capsync/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/capsync /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL Certificate (Let's Encrypt)

```bash
# Install SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

### Firewall Configuration

```bash
# Configure UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status
```

---

## 5. Monitoring & Maintenance

### Health Checks

```bash
# Check backend
curl http://localhost:8000/

# Check frontend
curl http://localhost/

# Check systemd service
sudo systemctl status capsync-backend
sudo journalctl -u capsync-backend -f
```

### Log Management

```bash
# View backend logs
sudo journalctl -u capsync-backend -n 100

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Monitoring Tools

**Option 1: Uptime Robot** (Free)
- Monitor: https://uptimerobot.com
- Setup HTTP(s) monitors for your domain

**Option 2: Sentry** (Error Tracking)
```bash
# Add to backend/api/requirements.txt
echo "sentry-sdk[fastapi]==1.40.0" >> requirements.txt
```

Add to `main.py`:
```python
import sentry_sdk
sentry_sdk.init(dsn="YOUR_SENTRY_DSN")
```

**Option 3: LogRocket** (Frontend Monitoring)
```bash
cd frontend
npm install logrocket
```

### Backup Strategy

```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/capsync"

# Create backup
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/capsync_$DATE.tar.gz /var/www/capsync

# Keep only last 7 backups
find $BACKUP_DIR -name "capsync_*.tar.gz" -mtime +7 -delete
```

---

## Performance Optimization

### Backend

1. **Use Gunicorn with Uvicorn workers**
   ```bash
   pip install gunicorn
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

2. **Enable caching** (Redis)
   ```bash
   sudo apt install redis-server
   pip install redis
   ```

### Frontend

1. **Enable compression** (Already in nginx.conf)
2. **Use CDN** for static assets (Cloudflare)
3. **Optimize images** before building

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python3.11 --version

# Check dependencies
source .venv/bin/activate
pip list

# Check port availability
sudo lsof -i :8000

# View detailed logs
sudo journalctl -u capsync-backend -xe
```

### Frontend 404s
```bash
# Check Nginx config
sudo nginx -t

# Check file permissions
ls -la /var/www/capsync/frontend/dist

# Restart Nginx
sudo systemctl restart nginx
```

### Whisper model issues
```bash
# Clear model cache
rm -rf ~/.cache/huggingface

# Manually download model
python -c "from faster_whisper import WhisperModel; WhisperModel('small')"
```

---

## Cost Comparison

| Platform | Frontend | Backend | Total/Month |
|----------|----------|---------|-------------|
| **Docker (VPS)** | $5 | $5 | $10 |
| **Vercel + Railway** | Free | $5 | $5 |
| **Render** | $0 | $7 | $7 |
| **DigitalOcean** | $6 | $6 | $12 |

---

## Next Steps

- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Add authentication
- [ ] Implement database
- [ ] Set up CI/CD
- [ ] Performance testing
- [ ] Security audit

---

**Questions?** Open an issue on GitHub or check the documentation.
