"""
Claude API Client
Handles AI code review requests
"""

import anthropic
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from config import settings

logger = logging.getLogger(__name__)

@dataclass
class ReviewIssue:
    line: int
    severity: str  # "low", "medium", "high"
    type: str  # "security", "performance", "style", "bug", "best-practice"
    message: str
    suggestion: str
    confidence: float

@dataclass
class CodeReviewResult:
    overall_score: int  # 1-10
    summary: str
    issues: List[ReviewIssue]
    suggestions: List[str]
    positive_feedback: List[str]

class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        self.model = "claude-3-sonnet-20240229"
    
    def is_available(self) -> bool:
        """Check if Claude API is available"""
        try:
            # Simple test call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.error(f"Claude API not available: {str(e)}")
            return False
    
    async def review_code_change(
        self,
        filename: str,
        diff: str,
        file_content: str = "",
        context: Dict[str, Any] = None
    ) -> CodeReviewResult:
        """
        Review a code change using Claude
        """
        try:
            prompt = self._build_review_prompt(filename, diff, file_content, context)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return self._parse_review_response(response.content[0].text)
        
        except Exception as e:
            logger.error(f"Error in Claude review: {str(e)}")
            # Return fallback response
            return CodeReviewResult(
                overall_score=7,
                summary="Unable to complete AI review due to technical issues.",
                issues=[],
                suggestions=["Please review the code manually."],
                positive_feedback=[]
            )
    
    def _build_review_prompt(
        self,
        filename: str,
        diff: str,
        file_content: str,
        context: Dict[str, Any]
    ) -> str:
        """Build the prompt for code review"""
        
        file_extension = filename.split('.')[-1] if '.' in filename else 'txt'
        
        prompt = f"""You are an expert code reviewer. Please review the following code change.

**File:** {filename}
**Language:** {file_extension}

**Code Diff:**
```diff
{diff}
```

**Full File Context (if available):**
```{file_extension}
{file_content[:3000] if file_content else "Not available"}
```

**Additional Context:**
{json.dumps(context, indent=2) if context else "None"}

Please provide a comprehensive code review focusing on:

1. **Code Quality**: Readability, maintainability, and clarity
2. **Security**: Potential vulnerabilities or security issues
3. **Performance**: Efficiency and resource usage
4. **Best Practices**: Language-specific conventions and patterns
5. **Bugs**: Potential runtime errors or logic issues
6. **Testing**: Test coverage and quality considerations

**Response Format:**
Please respond with a JSON object in this exact format:

```json
{{
  "overall_score": <integer 1-10>,
  "summary": "<brief overall assessment>",
  "issues": [
    {{
      "line": <line number from diff>,
      "severity": "<low|medium|high>",
      "type": "<security|performance|style|bug|best-practice>",
      "message": "<description of the issue>",
      "suggestion": "<specific suggestion to fix>",
      "confidence": <float 0.0-1.0>
    }}
  ],
  "suggestions": [
    "<general improvement suggestions>"
  ],
  "positive_feedback": [
    "<things done well>"
  ]
}}
```

**Important Guidelines:**
- Be constructive and specific
- Focus on the changed lines in the diff
- Provide actionable suggestions
- Consider the broader context of the codebase
- Be thorough but concise
- Only flag real issues, not stylistic preferences unless they impact readability
- Assign appropriate severity levels
- Include line numbers that correspond to the diff

Please analyze the code change and provide your review in the specified JSON format."""

        return prompt
    
    def _parse_review_response(self, response: str) -> CodeReviewResult:
        """Parse Claude's response into structured format"""
        try:
            # Extract JSON from response
            json_start = response.find('```json')
            json_end = response.find('```', json_start + 7)
            
            if json_start == -1 or json_end == -1:
                # Try to find JSON without markdown
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise ValueError("No JSON found in response")
                
                json_str = response[json_start:json_end]
            else:
                json_str = response[json_start + 7:json_end]
            
            data = json.loads(json_str)
            
            # Parse issues
            issues = []
            for issue_data in data.get('issues', []):
                issue = ReviewIssue(
                    line=issue_data.get('line', 0),
                    severity=issue_data.get('severity', 'medium'),
                    type=issue_data.get('type', 'general'),
                    message=issue_data.get('message', ''),
                    suggestion=issue_data.get('suggestion', ''),
                    confidence=issue_data.get('confidence', 0.8)
                )
                issues.append(issue)
            
            return CodeReviewResult(
                overall_score=data.get('overall_score', 7),
                summary=data.get('summary', 'Code review completed.'),
                issues=issues,
                suggestions=data.get('suggestions', []),
                positive_feedback=data.get('positive_feedback', [])
            )
            
        except Exception as e:
            logger.error(f"Error parsing Claude response: {str(e)}")
            logger.debug(f"Response was: {response}")
            
            # Return fallback response
            return CodeReviewResult(
                overall_score=7,
                summary="Review completed with parsing issues.",
                issues=[],
                suggestions=["Please review the code manually."],
                positive_feedback=[]
            )
    
    async def summarize_multiple_files(
        self,
        reviews: List[CodeReviewResult],
        pr_title: str,
        pr_description: str
    ) -> str:
        """
        Create a summary of multiple file reviews
        """
        try:
            prompt = f"""Please create a comprehensive summary of the following code reviews for a pull request.

**PR Title:** {pr_title}
**PR Description:** {pr_description}

**Individual File Reviews:**
{self._format_reviews_for_summary(reviews)}

Please provide a concise summary that includes:
1. Overall assessment of the PR
2. Key issues that need attention
3. Positive aspects of the code
4. Recommendations for improvement

Keep the summary professional and actionable."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error creating summary: {str(e)}")
            return "Summary generation failed. Please review individual file comments."
    
    def _format_reviews_for_summary(self, reviews: List[CodeReviewResult]) -> str:
        """Format reviews for summary prompt"""
        formatted = []
        
        for i, review in enumerate(reviews, 1):
            high_issues = [issue for issue in review.issues if issue.severity == 'high']
            medium_issues = [issue for issue in review.issues if issue.severity == 'medium']
            
            formatted.append(f"""
File {i}:
- Overall Score: {review.overall_score}/10
- Summary: {review.summary}
- High Priority Issues: {len(high_issues)}
- Medium Priority Issues: {len(medium_issues)}
- Key Issues: {[issue.message for issue in high_issues[:3]]}
""")
        
        return "\n".join(formatted)