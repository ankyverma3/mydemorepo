"""
GitHub API Client
Handles authentication and API interactions
"""

import jwt
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging

from config import settings

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self):
        self.app_id = settings.GITHUB_APP_ID
        self.private_key = settings.PRIVATE_KEY
        self.base_url = "https://api.github.com"
        self._installation_tokens = {}
    
    def generate_jwt(self) -> str:
        """Generate JWT for GitHub App authentication"""
        now = int(time.time())
        payload = {
            'iat': now - 60,  # Issued at time (1 minute ago)
            'exp': now + (10 * 60),  # Expiration time (10 minutes from now)
            'iss': self.app_id  # Issuer
        }
        
        return jwt.encode(payload, self.private_key, algorithm='RS256')
    
    async def get_installation_access_token(self, installation_id: int) -> str:
        """Get access token for installation"""
        # Check if we have a cached token
        if installation_id in self._installation_tokens:
            token_data = self._installation_tokens[installation_id]
            if datetime.now(timezone.utc) < token_data['expires_at']:
                return token_data['token']
        
        # Generate new token
        jwt_token = self.generate_jwt()
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        response = requests.post(
            f"{self.base_url}/app/installations/{installation_id}/access_tokens",
            headers=headers
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to get installation token: {response.text}")
        
        token_data = response.json()
        
        # Cache the token
        self._installation_tokens[installation_id] = {
            'token': token_data['token'],
            'expires_at': datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
        }
        
        return token_data['token']
    
    def _get_headers(self, token: str) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
    
    async def get_pull_request_files(
        self, 
        owner: str, 
        repo: str, 
        pull_number: int, 
        installation_id: int
    ) -> List[Dict]:
        """Get files changed in a pull request"""
        token = await self.get_installation_access_token(installation_id)
        headers = self._get_headers(token)
        
        response = requests.get(
            f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/files",
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get PR files: {response.text}")
        
        return response.json()
    
    async def get_pull_request(
        self, 
        owner: str, 
        repo: str, 
        pull_number: int, 
        installation_id: int
    ) -> Dict:
        """Get pull request details"""
        token = await self.get_installation_access_token(installation_id)
        headers = self._get_headers(token)
        
        response = requests.get(
            f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}",
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get PR: {response.text}")
        
        return response.json()
    
    async def create_review_comment(
        self, 
        owner: str, 
        repo: str, 
        pull_number: int, 
        body: str,
        commit_id: str,
        path: str,
        line: int,
        installation_id: int
    ) -> Dict:
        """Create a review comment on a specific line"""
        token = await self.get_installation_access_token(installation_id)
        headers = self._get_headers(token)
        
        data = {
            'body': body,
            'commit_id': commit_id,
            'path': path,
            'line': line
        }
        
        response = requests.post(
            f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/comments",
            json=data,
            headers=headers
        )
        
        if response.status_code != 201:
            logger.error(f"Failed to create review comment: {response.text}")
            raise Exception(f"Failed to create review comment: {response.text}")
        
        return response.json()
    
    async def create_pull_request_review(
        self, 
        owner: str, 
        repo: str, 
        pull_number: int, 
        body: str,
        event: str = "COMMENT",
        comments: List[Dict] = None,
        installation_id: int = None
    ) -> Dict:
        """Create a pull request review"""
        token = await self.get_installation_access_token(installation_id)
        headers = self._get_headers(token)
        
        data = {
            'body': body,
            'event': event
        }
        
        if comments:
            data['comments'] = comments
        
        response = requests.post(
            f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
            json=data,
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to create PR review: {response.text}")
            raise Exception(f"Failed to create PR review: {response.text}")
        
        return response.json()
    
    async def get_file_content(
        self, 
        owner: str, 
        repo: str, 
        path: str, 
        ref: str,
        installation_id: int
    ) -> str:
        """Get file content from repository"""
        token = await self.get_installation_access_token(installation_id)
        headers = self._get_headers(token)
        
        response = requests.get(
            f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            params={'ref': ref}
        )
        
        if response.status_code != 200:
            logger.warning(f"Failed to get file content for {path}: {response.text}")
            return ""
        
        import base64
        file_data = response.json()
        return base64.b64decode(file_data['content']).decode('utf-8')
    
    async def create_check_run(
        self,
        owner: str,
        repo: str,
        name: str,
        head_sha: str,
        status: str,
        conclusion: str = None,
        output: Dict = None,
        installation_id: int = None
    ) -> Dict:
        """Create a check run for the PR"""
        token = await self.get_installation_access_token(installation_id)
        headers = self._get_headers(token)
        
        data = {
            'name': name,
            'head_sha': head_sha,
            'status': status
        }
        
        if conclusion:
            data['conclusion'] = conclusion
        
        if output:
            data['output'] = output
        
        response = requests.post(
            f"{self.base_url}/repos/{owner}/{repo}/check-runs",
            json=data,
            headers=headers
        )
        
        if response.status_code != 201:
            logger.error(f"Failed to create check run: {response.text}")
            raise Exception(f"Failed to create check run: {response.text}")
        
        return response.json()