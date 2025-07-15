"""
Webhook Handler
Processes GitHub webhook events
"""

import logging
from typing import Dict, List, Any
import asyncio
from datetime import datetime

from github_client import GitHubClient
from claude_client import ClaudeClient, CodeReviewResult
from models import ReviewResult

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self, github_client: GitHubClient, claude_client: ClaudeClient):
        self.github_client = github_client
        self.claude_client = claude_client
        self.review_cache = {}
    
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]):
        """
        Main webhook handler that routes events to appropriate handlers
        """
        try:
            if event_type == "pull_request":
                await self._handle_pull_request_event(payload)
            elif event_type == "pull_request_review":
                await self._handle_pull_request_review_event(payload)
            elif event_type == "installation":
                await self._handle_installation_event(payload)
            else:
                logger.info(f"Unhandled event type: {event_type}")
        
        except Exception as e:
            logger.error(f"Error handling webhook {event_type}: {str(e)}")
    
    async def _handle_pull_request_event(self, payload: Dict[str, Any]):
        """Handle pull request events"""
        action = payload.get("action")
        
        if action in ["opened", "synchronize", "reopened"]:
            pr = payload["pull_request"]
            repository = payload["repository"]
            installation = payload["installation"]
            
            await self.process_pull_request_review(
                owner=repository["owner"]["login"],
                repo=repository["name"],
                pull_number=pr["number"],
                installation_id=installation["id"],
                pr_data=pr
            )
    
    async def _handle_pull_request_review_event(self, payload: Dict[str, Any]):
        """Handle pull request review events"""
        logger.info(f"PR review event: {payload.get('action')}")
        # Handle review-related events if needed
    
    async def _handle_installation_event(self, payload: Dict[str, Any]):
        """Handle installation events"""
        action = payload.get("action")
        logger.info(f"Installation event: {action}")
        # Handle app installation/uninstallation
    
    async def process_pull_request_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        installation_id: int,
        pr_data: Dict = None
    ):
        """
        Process a pull request for code review
        """
        cache_key = f"{owner}/{repo}/pull/{pull_number}"
        
        try:
            # Update cache with processing status
            self.review_cache[cache_key] = ReviewResult(
                status="processing",
                timestamp=datetime.utcnow().isoformat(),
                summary="Starting code review..."
            )
            
            logger.info(f"Processing PR review for {cache_key}")
            
            # Get PR details if not provided
            if not pr_data:
                pr_data = await self.github_client.get_pull_request(
                    owner, repo, pull_number, installation_id
                )
            
            # Get changed files
            files = await self.github_client.get_pull_request_files(
                owner, repo, pull_number, installation_id
            )
            
            # Filter files to review
            reviewable_files = self._filter_reviewable_files(files)
            
            if not reviewable_files:
                logger.info(f"No reviewable files found in PR {cache_key}")
                self.review_cache[cache_key] = ReviewResult(
                    status="completed",
                    timestamp=datetime.utcnow().isoformat(),
                    summary="No files to review"
                )
                return
            
            # Review each file
            file_reviews = []
            review_comments = []
            
            for file in reviewable_files:
                try:
                    # Get file content for context
                    file_content = ""
                    if file.get("status") != "removed":
                        try:
                            file_content = await self.github_client.get_file_content(
                                owner, repo, file["filename"], 
                                pr_data["head"]["sha"], installation_id
                            )
                        except Exception as e:
                            logger.warning(f"Could not get file content for {file['filename']}: {str(e)}")
                    
                    # Review the file
                    review = await self.claude_client.review_code_change(
                        filename=file["filename"],
                        diff=file.get("patch", ""),
                        file_content=file_content,
                        context={
                            "additions": file.get("additions", 0),
                            "deletions": file.get("deletions", 0),
                            "changes": file.get("changes", 0),
                            "status": file.get("status", "modified")
                        }
                    )
                    
                    file_reviews.append(review)
                    
                    # Convert review to GitHub comments
                    comments = self._convert_review_to_comments(
                        review, file, pr_data["head"]["sha"]
                    )
                    review_comments.extend(comments)
                    
                except Exception as e:
                    logger.error(f"Error reviewing file {file['filename']}: {str(e)}")
                    continue
            
            # Create overall summary
            summary = await self.claude_client.summarize_multiple_files(
                file_reviews,
                pr_data.get("title", ""),
                pr_data.get("body", "")
            )
            
            # Post review to GitHub
            await self._post_review_to_github(
                owner, repo, pull_number, installation_id,
                summary, review_comments
            )
            
            # Update cache with completion
            self.review_cache[cache_key] = ReviewResult(
                status="completed",
                timestamp=datetime.utcnow().isoformat(),
                summary=summary,
                files_reviewed=len(reviewable_files),
                total_issues=sum(len(review.issues) for review in file_reviews)
            )
            
            logger.info(f"Completed PR review for {cache_key}")
            
        except Exception as e:
            logger.error(f"Error processing PR review {cache_key}: {str(e)}")
            self.review_cache[cache_key] = ReviewResult(
                status="error",
                timestamp=datetime.utcnow().isoformat(),
                summary=f"Review failed: {str(e)}"
            )
    
    def _filter_reviewable_files(self, files: List[Dict]) -> List[Dict]:
        """Filter files that should be reviewed"""
        reviewable_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.sql', '.html', '.css', '.scss', '.less', '.vue', '.svelte'
        }
        
        skip_patterns = {
            'package-lock.json', 'yarn.lock', 'poetry.lock', 'Pipfile.lock',
            '.min.js', '.min.css', '.bundle.js', '.bundle.css',
            'node_modules/', 'vendor/', 'dist/', 'build/', '.git/',
            '__pycache__/', '.pytest_cache/', '.mypy_cache/',
            '.generated.', '.auto.', 'migrations/', 'locale/'
        }
        
        reviewable_files = []
        
        for file in files:
            filename = file.get('filename', '')
            
            # Skip removed files
            if file.get('status') == 'removed':
                continue
            
            # Skip files that are too large
            if file.get('changes', 0) > 1000:
                logger.info(f"Skipping large file: {filename} ({file.get('changes')} changes)")
                continue
            
            # Check file extension
            has_reviewable_extension = any(
                filename.endswith(ext) for ext in reviewable_extensions
            )
            
            # Check skip patterns
            should_skip = any(
                pattern in filename for pattern in skip_patterns
            )
            
            if has_reviewable_extension and not should_skip:
                reviewable_files.append(file)
            else:
                logger.debug(f"Skipping file: {filename}")
        
        return reviewable_files
    
    def _convert_review_to_comments(
        self, 
        review: CodeReviewResult, 
        file: Dict, 
        commit_sha: str
    ) -> List[Dict]:
        """Convert review result to GitHub review comments"""
        comments = []
        
        for issue in review.issues:
            if issue.line > 0:  # Only add comments for specific lines
                severity_emoji = {
                    'high': '🚨',
                    'medium': '⚠️',
                    'low': '💡'
                }
                
                type_emoji = {
                    'security': '🔒',
                    'performance': '⚡',
                    'bug': '🐛',
                    'style': '✨',
                    'best-practice': '📚'
                }
                
                comment_body = f"""
{severity_emoji.get(issue.severity, '💡')} {type_emoji.get(issue.type, '📝')} **{issue.type.title()} Issue ({issue.severity} severity)**

{issue.message}

**Suggestion:** {issue.suggestion}

*Confidence: {issue.confidence:.0%}*
"""
                
                comments.append({
                    'path': file['filename'],
                    'line': issue.line,
                    'body': comment_body.strip()
                })
        
        return comments
    
    async def _post_review_to_github(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        installation_id: int,
        summary: str,
        comments: List[Dict]
    ):
        """Post the review to GitHub"""
        try:
            # Create review summary
            review_body = f"""## 🤖 AI Code Review Summary

{summary}

---

*This review was generated by AI. Please use your judgment when applying suggestions.*
"""
            
            # Create the review
            await self.github_client.create_pull_request_review(
                owner=owner,
                repo=repo,
                pull_number=pull_number,
                body=review_body,
                event="COMMENT",
                comments=comments[:50],  # Limit to 50 comments to avoid spam
                installation_id=installation_id
            )
            
            logger.info(f"Posted review with {len(comments)} comments to PR #{pull_number}")
            
        except Exception as e:
            logger.error(f"Error posting review to GitHub: {str(e)}")
            raise