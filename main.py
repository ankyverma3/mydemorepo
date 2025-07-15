"""
FastAPI GitHub App for AI Code Review
Main application file
"""

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import asyncio
from typing import Dict, List, Optional
import logging
from datetime import datetime

from github_client import GitHubClient
from claude_client import ClaudeClient
from webhook_handler import WebhookHandler
from code_review import CodeReviewer
from models import WebhookPayload, ReviewResult
from utils import verify_webhook_signature, setup_logging
from config import settings

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Code Review Bot",
    description="GitHub App that provides AI-powered code reviews using Claude",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize clients
github_client = GitHubClient()
claude_client = ClaudeClient()
webhook_handler = WebhookHandler(github_client, claude_client)
code_reviewer = CodeReviewer(claude_client)

# In-memory store for tracking reviews (use Redis in production)
review_cache: Dict[str, ReviewResult] = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Code Review Bot",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "github_app_id": settings.GITHUB_APP_ID,
        "claude_available": claude_client.is_available(),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle GitHub webhook events
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature
        signature = request.headers.get("X-Hub-Signature-256")
        if not verify_webhook_signature(body, signature, settings.WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse payload
        payload = await request.json()
        
        # Log the event
        event_type = request.headers.get("X-GitHub-Event")
        logger.info(f"Received GitHub event: {event_type}")
        
        # Handle the webhook in background
        background_tasks.add_task(
            webhook_handler.handle_webhook,
            event_type,
            payload
        )
        
        return {"status": "accepted"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/reviews/{repo_owner}/{repo_name}/pull/{pull_number}")
async def get_review_status(
    repo_owner: str,
    repo_name: str,
    pull_number: int
):
    """
    Get the status of a code review
    """
    cache_key = f"{repo_owner}/{repo_name}/pull/{pull_number}"
    
    if cache_key in review_cache:
        return review_cache[cache_key]
    
    return {"status": "not_found", "message": "No review found for this PR"}

@app.post("/reviews/{repo_owner}/{repo_name}/pull/{pull_number}/trigger")
async def trigger_review(
    repo_owner: str,
    repo_name: str,
    pull_number: int,
    background_tasks: BackgroundTasks
):
    """
    Manually trigger a code review for a PR
    """
    try:
        # Add review task to background
        background_tasks.add_task(
            webhook_handler.process_pull_request_review,
            repo_owner,
            repo_name,
            pull_number,
            installation_id=None  # Will be fetched from GitHub
        )
        
        return {"status": "triggered", "message": "Review started"}
        
    except Exception as e:
        logger.error(f"Error triggering review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to trigger review")

@app.get("/stats")
async def get_stats():
    """
    Get service statistics
    """
    return {
        "total_reviews": len(review_cache),
        "recent_reviews": [
            {
                "key": key,
                "status": review.status,
                "timestamp": review.timestamp
            }
            for key, review in list(review_cache.items())[-10:]
        ]
    } 