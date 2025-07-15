# AI Code Review Bot

A FastAPI-based GitHub App that provides AI-powered code reviews using Claude API. This bot automatically reviews pull requests and provides intelligent feedback on code quality, security, performance, and best practices.

## Features

- 🤖 **AI-Powered Reviews**: Uses Claude API for intelligent code analysis
- 🔒 **Security Scanning**: Detects common security vulnerabilities
- 📊 **Code Quality Assessment**: Analyzes code maintainability and readability
- ⚡ **Performance Insights**: Identifies potential performance issues
- 🎯 **Best Practices**: Enforces language-specific coding standards
- 📝 **Inline Comments**: Provides specific feedback on problematic lines
- 📋 **Review Summaries**: Generates comprehensive PR review summaries
- 🔄 **Real-time Processing**: Responds to PR events automatically

## Quick Start

### 1. Prerequisites

- Python 3.11+
- GitHub App with appropriate permissions
- Claude API key from Anthropic

### 2. Setup GitHub App

1. Go to GitHub Settings → Developer settings → GitHub Apps
2. Click "New GitHub App"
3. Configure with these permissions:
   - Repository permissions:
     - Contents: Read
     - Metadata: Read
     - Pull requests: Write
     - Checks: Write (optional)
   - Subscribe to events:
     - Pull request
     - Push (optional)

4. Generate and download private key
5. Install the app on your repositories

### 3. Environment Configuration

Create a `.env` file:

```bash
# GitHub App Configuration
GITHUB_APP_ID=your_github_app_id
WEBHOOK_SECRET=your_webhook_secret
PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
your_private_key_content
-----END RSA PRIVATE KEY-----"

# Claude API Configuration
CLAUDE_API_KEY=your_claude_api_key

# Server Configuration
PORT=8000
DEBUG=false
```

### 4. Installation

```bash
pip install -r requirements.txt

# Run the app
uvicorn main:app --reload
```