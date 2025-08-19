# app/main.py
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.gmail_responder_routes import router as gmail_responder_router
from routes.gmail_summary_routes import router as gmail_summary_router
from routes.oAuth_handling import router as oauth_router

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount workflow specific routers
app.include_router(gmail_responder_router, tags=["gmail-ai-responder"])
app.include_router(gmail_summary_router, tags=["gmail-summary"])
app.include_router(oauth_router, tags=["oauth"])

@app.get("/health")
def health():
    return {"ok": True}
