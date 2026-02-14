# Hybrid Deployment: Vercel + Railway

## 🎯 Best Solution for Capsync

Due to Whisper model size (>250MB), we use a **hybrid approach**:
- **Frontend**: Vercel (Free, Fast CDN)
- **Backend**: Railway ($5/month, No size limits)

---

## Quick Setup

### Part 1: Deploy Backend to Railway (5 minutes)

1. **Go to Railway**:
   - Visit [railway.app](https://railway.app)
   - Sign in with GitHub

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `capsync` repository

3. **Configure Service**:
   ```
   Name: capsync-backend
   Root Directory: backend/api
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

4. **Environment Variables**:
   ```
   WHISPER_MODEL=small
   WHISPER_COMPUTE=int8
   PORT=${{PORT}}
   ```

5. **Deploy & Get URL**:
   - Railway will provide a URL like: `capsync-backend-production.up.railway.app`
   - **Copy this URL!**

---

### Part 2: Deploy Frontend to Vercel (3 minutes)

1. **Update vercel.json**:
   
   Edit the `VITE_API_BASE` in `vercel.json`:
   ```json
   {
     "build": {
       "env": {
         "VITE_API_BASE": "https://capsync-backend-production.up.railway.app"
       }
     }
   }
   ```

2. **Deploy to Vercel**:
   ```bash
   vercel --prod
   ```

3. **Or Set Environment Variable**:
   ```bash
   vercel env add VITE_API_BASE production
   # Enter your Railway URL: https://your-backend.railway.app
   
   vercel --prod
   ```

---

## Alternative: Use OpenAI Whisper API

Instead of hosting Whisper yourself, use OpenAI's API:

### Backend Changes

1. **Update requirements.txt**:
   ```
   fastapi==0.115.0
   openai>=1.0.0
   python-multipart==0.0.9
   ```

2. **Update main.py**:
   ```python
   from openai import OpenAI
   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
   
   @app.post("/transcribe")
   async def transcribe(file: UploadFile = File(...)):
       with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
           content = await file.read()
           tmp.write(content)
           tmp_path = tmp.name
       
       with open(tmp_path, "rb") as audio_file:
           transcript = client.audio.transcriptions.create(
               model="whisper-1",
               file=audio_file,
               response_format="verbose_json"
           )
       
       segments = []
       for seg in transcript.segments:
           segments.append(Segment(
               id=str(uuid.uuid4()),
               start=seg['start'],
               end=seg['end'],
               text=seg['text']
           ))
       
       return TranscribeResponse(segments=segments)
   ```

3. **Deploy to Vercel**:
   - Set `OPENAI_API_KEY` in Vercel env
   - Deploy: `vercel --prod`
   - **This will work!**

---

## Cost Comparison

| Setup | Frontend | Backend | Total/Month |
|-------|----------|---------|-------------|
| **Vercel + Railway** | Free | $5 | $5 |
| **Vercel + OpenAI API** | Free | ~$1-2* | $1-2 |
| **Render Full-Stack** | $0 | $7 | $7 |

*Based on usage (OpenAI charges per minute of audio)

---

## Recommended: Vercel + Railway

This is the **best balance** of cost and simplicity:

✅ Free CDN for frontend  
✅ Fast global delivery  
✅ $5/month backend (no limits)  
✅ Full Whisper model support  
✅ No API usage charges  
✅ Complete control  

---

## Complete Railway Setup

### 1. Create railway.toml (Optional)

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
```

### 2. GitHub Auto-Deploy

Railway automatically deploys on every push to `main`!

### 3. Custom Domain (Optional)

Add your domain in Railway settings for free HTTPS.

---

## Testing Your Setup

### Test Backend (Railway)
```bash
curl https://your-backend.railway.app/
```

### Test Frontend (Vercel)
```bash
# Should show your React app
open https://your-app.vercel.app
```

### Test Full Flow
1. Upload a video
2. Click "Generate Captions"
3. Check Network tab - should call Railway URL
4. Should see captions!

---

## Deploy Commands

### Railway
```bash
# Deploy via GitHub (recommended)
git push origin main

# Or use Railway CLI
npm i -g @railway/cli
railway login
railway up
```

### Vercel
```bash
# Update environment variable
vercel env add VITE_API_BASE production

# Deploy
vercel --prod
```

---

## Troubleshooting

### Frontend can't reach backend

**CORS Issue**: Update `backend/api/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app.vercel.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Railway deployment fails

Check logs:
```bash
railway logs
```

Common fixes:
- Ensure Python 3.11 in runtime
- Check requirements.txt format
- Verify start command

---

## Final Deployment URLs

After setup, you'll have:

```
Frontend: https://capsync.vercel.app
Backend:  https://capsync-backend.up.railway.app
API Docs: https://capsync-backend.up.railway.app/docs
```

**Total Time**: 10 minutes  
**Total Cost**: $5/month  

🚀 **This is the recommended production setup!**
