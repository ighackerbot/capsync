from mangum import Mangum
from main import app

# Vercel serverless handler
# This wraps the FastAPI app for deployment on Vercel
handler = Mangum(app, lifespan="off")
