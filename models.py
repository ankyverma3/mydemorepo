"""
Data models for the application
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

class WebhookPayload(BaseModel):
    """GitHub webhook payload model"""
    action: str
    pull_request: Optional[Dict[str, Any]] = None
    repository: Optional[Dict[str, Any]] = None
    installation: Optional[Dict[str, Any]] = None
    sender: Optional[Dict[str, Any]] = None

class ReviewResult(BaseModel):
    """Code review result model"""
    status: str  # "processing", "completed", "error"
    timestamp: str
    summary: str
    files_reviewed: Optional[int] = 0
    total_issues: Optional[int] = 0
    error_message: Optional[str] = None

class FileReview(BaseModel):
    """Individual file review model"""
    filename: str
    score: int
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    positive_feedback: List[str]

class PRReviewRequest(BaseModel):
    """Manual PR review request model"""
    repository: str
    pull_number: int
    force_review: bool = False