# Vercel Full-Stack Deployment Guide

## 🚀 Deploy Both Frontend & Backend to Vercel

Vercel now supports full-stack applications with serverless functions. Deploy your entire Capsync app to Vercel with a single command!

---

## Quick Deploy (Recommended)

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Login to Vercel

```bash
vercel login
```

### Step 3: Deploy

```bash
# From project root
cd /Users/anujjain/capsync-5
vercel --prod
```

That's it! Vercel will automatically:
- Build and deploy your React frontend
- Deploy your FastAPI backend as serverless functions
- Set up routing between them
- Provide you with a production URL

---

## Project Setup

### 1. Vercel Configuration

We've created a `vercel.json` file that handles:
- Frontend build with Vite
- Backend serverless functions
- API routing to `/api/*`
- Environment variables

**File**: `vercel.json`
```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": { "distDir": "dist" }
    },
    {
      "src": "backend/api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "backend/api/main.py" },
    { "src": "/(.*)", "dest": "frontend/$1" }
  ]
}
```

### 2. Frontend Build Script

Add to `frontend/package.json`:
```json
{
  "scripts": {
    "build": "vite build",
    "vercel-build": "vite build"
  }
}
```

### 3. Backend Requirements

Ensure `backend/api/requirements.txt` includes:
```
fastapi==0.115.0
mangum>=0.17.0
faster-whisper==1.0.3
numpy>=1.23.0
python-multipart==0.0.9
```

**Note**: `mangum` is required to wrap FastAPI for AWS Lambda/Vercel serverless.

### 4. API Adapter for Vercel

Create `backend/api/vercel_app.py`:

```python
from mangum import Mangum
from main import app

# Wrap FastAPI app for Vercel serverless
handler = Mangum(app)
```

---

## Environment Variables

### Set in Vercel Dashboard

1. Go to your project on [vercel.com](https://vercel.com)
2. Navigate to **Settings** → **Environment Variables**
3. Add these variables:

| Variable | Value | Environment |
|----------|-------|-------------|
| `WHISPER_MODEL` | `small` | Production |
| `WHISPER_COMPUTE` | `int8` | Production |
| `VITE_API_BASE` | `/api` | Production |

### Or via CLI

```bash
vercel env add WHISPER_MODEL production
# Enter: small

vercel env add WHISPER_COMPUTE production
# Enter: int8

vercel env add VITE_API_BASE production
# Enter: /api
```

---

## Deployment Options

### Option 1: Automatic GitHub Deployment (Recommended)

1. **Connect GitHub Repository**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Click "Import Project"
   - Select your GitHub repository
   - Vercel will auto-detect the configuration

2. **Configure Project**
   - Root Directory: `./`
   - Framework Preset: `Vite`
   - Build Command: `cd frontend && npm run build`
   - Output Directory: `frontend/dist`

3. **Add Environment Variables** (as shown above)

4. **Deploy**
   - Click "Deploy"
   - Every push to `main` branch auto-deploys!

### Option 2: CLI Deployment

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod

# Deploy specific branch
vercel --prod --branch=main
```

### Option 3: One-Click Deploy Button

Add to your README:

```markdown
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/capsync)
```

---

## Project Structure for Vercel

```
capsync-5/
├── frontend/
│   ├── dist/              # Built files (auto-created)
│   ├── src/
│   ├── package.json       # Must have "vercel-build" script
│   └── vite.config.js
│
├── backend/
│   ├── api/
│   │   ├── main.py        # FastAPI app
│   │   ├── vercel_app.py  # Vercel adapter (NEW)
│   │   └── requirements.txt
│   └── services/
│
├── vercel.json            # Vercel configuration (NEW)
└── .gitignore
```

---

## API Routes

After deployment, your API will be available at:

```
https://your-app.vercel.app/api/transcribe
https://your-app.vercel.app/api/render
https://your-app.vercel.app/api/docs
```

Frontend will be at:
```
https://your-app.vercel.app/
```

---

## Limitations & Considerations

### Vercel Serverless Limits

| Resource | Free Plan | Pro Plan |
|----------|-----------|----------|
| **Function Duration** | 10s | 60s |
| **Function Size** | 50MB | 50MB |
| **Bandwidth** | 100GB/month | 1TB/month |
| **Executions** | 100K/month | 1M/month |

### Important Notes

1. **Whisper Model Size**
   - Use `tiny` or `base` model for faster cold starts
   - `small` model may timeout on free plan
   - Consider upgrading to Pro for `medium`/`large`

2. **Video Processing**
   - Large videos may exceed function timeout
   - Consider limiting video length to 30-60 seconds
   - Or use Vercel Pro for longer timeouts

3. **Cold Starts**
   - First request may take 5-10 seconds
   - Subsequent requests are faster
   - Keep functions warm with uptime monitoring

---

## Optimizations

### 1. Reduce Cold Start Time

**Use smaller Whisper model**:
```bash
vercel env add WHISPER_MODEL production
# Enter: tiny  # Or 'base' for better accuracy
```

### 2. Function Region

Set in `vercel.json`:
```json
{
  "functions": {
    "backend/api/main.py": {
      "memory": 3008,
      "maxDuration": 60,
      "regions": ["iad1"]
    }
  }
}
```

### 3. Enable Edge Caching

```json
{
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "s-maxage=1, stale-while-revalidate"
        }
      ]
    }
  ]
}
```

---

## Custom Domain

### Add Custom Domain

1. Go to your project settings
2. Navigate to **Domains**
3. Add your domain (e.g., `capsync.yourdomain.com`)
4. Update DNS records as instructed
5. SSL certificate is auto-provisioned!

---

## Monitoring

### Built-in Analytics

Vercel provides:
- Real-time analytics
- Function logs
- Error tracking
- Performance metrics

Access at: `https://vercel.com/yourteam/capsync/analytics`

### View Logs

```bash
# View deployment logs
vercel logs

# View function logs
vercel logs --follow
```

---

## Troubleshooting

### Backend Not Working

**Check function logs**:
```bash
vercel logs --follow
```

**Common issues**:
1. Missing `mangum` in requirements.txt
2. Function timeout (switch to smaller model)
3. Missing environment variables

### Build Failures

**Frontend build fails**:
```bash
# Test build locally
cd frontend
npm run build
```

**Backend build fails**:
- Check Python version (must be 3.9, 3.10, or 3.11)
- Verify all dependencies in requirements.txt

### API Routes Not Working

Check `vercel.json` routes:
- API routes should be before catch-all route
- Frontend route should be last

---

## Cost Estimate

### Free Hobby Plan
- Perfect for personal projects
- 100GB bandwidth
- 100K function executions
- **Cost**: $0/month

### Pro Plan
- Better for production
- 1TB bandwidth
- 1M function executions
- Longer function timeouts (60s)
- **Cost**: $20/month

---

## Complete Deployment Checklist

- [ ] Install Vercel CLI: `npm install -g vercel`
- [ ] Create `vercel.json` configuration
- [ ] Add `mangum` to backend requirements
- [ ] Create `vercel_app.py` adapter
- [ ] Set environment variables in Vercel
- [ ] Test build locally: `cd frontend && npm run build`
- [ ] Deploy: `vercel --prod`
- [ ] Test deployed app
- [ ] Connect custom domain (optional)
- [ ] Set up GitHub auto-deploy (optional)

---

## Alternative: Vercel + External Backend

If Whisper processing is too heavy for serverless:

**Frontend**: Deploy to Vercel  
**Backend**: Deploy to Railway/Render  

Update `VITE_API_BASE`:
```bash
vercel env add VITE_API_BASE production
# Enter: https://your-backend.railway.app
```

---

## Support

- **Vercel Docs**: https://vercel.com/docs
- **Vercel Discord**: https://vercel.com/discord
- **FastAPI + Vercel**: https://vercel.com/guides/python-fastapi

---

## Next Steps

1. Deploy to Vercel: `vercel --prod`
2. Test your deployment
3. Share your live URL!
4. Consider upgrading to Pro if needed

**Your Capsync app will be live in minutes!** 🚀
