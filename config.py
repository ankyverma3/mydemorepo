"""
Configuration settings
"""

import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

class Settings:
    def __init__(self):
        # GitHub App Configuration
        self.GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
        self.PRIVATE_KEY = self._load_private_key()
        self.WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
        
        # Claude API Configuration
        self.CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
        
        # Server Configuration
        self.PORT = int(os.getenv("PORT", 8000))
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        
        # Validate required settings
        self._validate_settings()
    
    def _load_private_key(self) -> str:
        """Load GitHub App private key from environment or file"""
        # Try to load from environment variable first
        private_key = os.getenv("PRIVATE_KEY")
        if private_key:
            return private_key
        
        # Try to load from file
        private_key_path = os.getenv("PRIVATE_KEY_PATH")
        if private_key_path and os.path.exists(private_key_path):
            with open(private_key_path, 'r') as f:
                return f.read()
        
        raise ValueError("Private key not found in PRIVATE_KEY or PRIVATE_KEY_PATH")
    
    def _validate_settings(self):
        """Validate that all required settings are present"""
        required_settings = [
            ("GITHUB_APP_ID", self.GITHUB_APP_ID),
            ("PRIVATE_KEY", self.PRIVATE_KEY),
            ("WEBHOOK_SECRET", self.WEBHOOK_SECRET),
            ("CLAUDE_API_KEY", self.CLAUDE_API_KEY),
        ]
        
        missing_settings = []
        for name, value in required_settings:
            if not value:
                missing_settings.append(name)
        
        if missing_settings:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_settings)}")

# Global settings instance
settings = Settings()