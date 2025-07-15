"""
Utility functions
"""

import hmac
import hashlib
import logging
import sys
from typing import Optional

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature
    """
    if not signature:
        return False
    
    expected_signature = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def setup_logging():
    """
    Setup logging configuration
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )
    
    # Set specific log levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def truncate_text(text: str, max_length: int = 1000) -> str:
    """
    Truncate text to maximum length
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def get_file_language(filename: str) -> str:
    """
    Get programming language from filename
    """
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sql': 'sql',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.less': 'less',
        '.vue': 'vue',
        '.svelte': 'svelte'
    }
    
    for ext, lang in extension_map.items():
        if filename.endswith(ext):
            return lang
    
    return 'text'

def parse_log_entry(log: str) -> Dict[str, str]:
    """
    Parses a log string and extracts key information into a dictionary.
    
    Parameters:
        log (str): Unstructured log line.
    
    Returns:
        dict: Structured log info.
    """
    result = {}

    # Extract log level
    level_match = re.search(r"\[(\w+)\]", log)
    if level_match:
        result["level"] = level_match.group(1)

    # Extract timestamp
    timestamp_match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", log)
    if timestamp_match:
        result["timestamp"] = timestamp_match.group(0)

    # Extract key-value pairs like user=anurag
    for match in re.findall(r"(\w+)=([^\s]+)", log):
        key, value = match
        result[key] = value

    # Extract status from "status:failed"
    status_match = re.search(r"status:([^\s-]+)", log)
    if status_match:
        result["status"] = status_match.group(1)

    # Extract message after the last dash
    message_match = re.search(r"- (.+)$", log)
    if message_match:
        result["message"] = message_match.group(1).strip()

    return result
