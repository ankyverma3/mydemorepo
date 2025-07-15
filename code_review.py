"""
Code Reviewer
Advanced code review logic and utilities
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from claude_client import ClaudeClient, CodeReviewResult
from utils import get_file_language, truncate_text

logger = logging.getLogger(__name__)

@dataclass
class ReviewContext:
    """Context for code review"""
    pr_title: str
    pr_description: str
    changed_files: List[str]
    total_additions: int
    total_deletions: int
    author: str
    is_draft: bool

class CodeReviewer:
    def __init__(self, claude_client: ClaudeClient):
        self.claude_client = claude_client
        self.security_patterns = self._load_security_patterns()
    
    def _load_security_patterns(self) -> Dict[str, List[str]]:
        """Load security vulnerability patterns"""
        return {
            'sql_injection': [
                r'SELECT.*\+.*',
                r'INSERT.*\+.*',
                r'UPDATE.*\+.*',
                r'DELETE.*\+.*',
                r'query\s*\+\s*',
                r'execute\s*\(\s*[\'"].*\+.*[\'"]'
            ],
            'xss': [
                r'innerHTML\s*=\s*.*\+',
                r'document\.write\s*\(\s*.*\+',
                r'eval\s*\(\s*.*\+',
                r'dangerouslySetInnerHTML'
            ],
            'path_traversal': [
                r'\.\./',
                r'\.\.\\',
                r'path\.join\s*\(\s*.*\+',
                r'os\.path\.join\s*\(\s*.*\+'
            ],
            'hardcoded_secrets': [
                r'password\s*=\s*[\'"][^\'\"]{8,}[\'"]',
                r'api_key\s*=\s*[\'"][^\'\"]{20,}[\'"]',
                r'secret\s*=\s*[\'"][^\'\"]{16,}[\'"]',
                r'token\s*=\s*[\'"][^\'\"]{20,}[\'"]'
            ]
        }
    
    async def enhanced_review(
        self,
        filename: str,
        diff: str,
        file_content: str,
        context: ReviewContext
    ) -> CodeReviewResult:
        """
        Enhanced code review with additional analysis
        """
        # Pre-process the diff
        processed_diff = self._preprocess_diff(diff)
        
        # Quick security scan
        security_issues = self._quick_security_scan(processed_diff, filename)
        
        # Detect code smells
        code_smells = self._detect_code_smells(processed_diff, filename)
        
        # Get AI review
        ai_review = await self.claude_client.review_code_change(
            filename=filename,
            diff=processed_diff,
            file_content=file_content,
            context={
                'pr_context': context.__dict__,
                'language': get_file_language(filename),
                'security_findings': security_issues,
                'code_smells': code_smells
            }
        )
        
        # Merge findings
        return self._merge_findings(ai_review, security_issues, code_smells)
    
    def _preprocess_diff(self, diff: str) -> str:
        """Preprocess diff to highlight important changes"""
        lines = diff.split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip context lines that are too long
            if line.startswith(' ') and len(line) > 200:
                processed_lines.append(' ' + truncate_text(line[1:], 100))
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _quick_security_scan(self, diff: str, filename: str) -> List[Dict[str, Any]]:
        """Quick security vulnerability scan"""
        issues = []
        language = get_file_language(filename)
        
        # Get added lines only
        added_lines = []
        for line_num, line in enumerate(diff.split('\n'), 1):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append((line_num, line[1:]))  # Remove the '+'
        
        # Check each security pattern
        for vuln_type, patterns in self.security_patterns.items():
            for pattern in patterns:
                for line_num, line in added_lines:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append({
                            'type': 'security',
                            'subtype': vuln_type,
                            'line': line_num,
                            'message': f'Potential {vuln_type.replace("_", " ")} vulnerability detected',
                            'code': line.strip(),
                            'severity': 'high'
                        })
        
        return issues
    
    def _detect_code_smells(self, diff: str, filename: str) -> List[Dict[str, Any]]:
        """Detect common code smells"""
        issues = []
        language = get_file_language(filename)
        
        # Get added lines
        added_lines = []
        for line_num, line in enumerate(diff.split('\n'), 1):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append((line_num, line[1:]))
        
        # Check for various code smells
        for line_num, line in added_lines:
            stripped_line = line.strip()
            
            # Long lines
            if len(stripped_line) > 120:
                issues.append({
                    'type': 'style',
                    'line': line_num,
                    'message': f'Line too long ({len(stripped_line)} characters)',
                    'severity': 'low'
                })
            
            # TODO comments
            if 'TODO' in stripped_line or 'FIXME' in stripped_line:
                issues.append({
                    'type': 'best-practice',
                    'line': line_num,
                    'message': 'TODO/FIXME comment should be addressed',
                    'severity': 'medium'
                })
            
            # Debug statements
            debug_patterns = ['console.log', 'print(', 'System.out.println', 'Debug.Log']
            for pattern in debug_patterns:
                if pattern in stripped_line:
                    issues.append({
                        'type': 'best-practice',
                        'line': line_num,
                        'message': f'Debug statement ({pattern}) should be removed',
                        'severity': 'low'
                    })
            
            # Language-specific checks
            if language == 'python':
                issues.extend(self._python_specific_checks(line_num, stripped_line))
            elif language == 'javascript':
                issues.extend(self._javascript_specific_checks(line_num, stripped_line))
        
        return issues
    
    def _python_specific_checks(self, line_num: int, line: str) -> List[Dict[str, Any]]:
        """Python-specific code quality checks"""
        issues = []
        
        # Bare except
        if re.search(r'except\s*:', line):
            issues.append({
                'type': 'best-practice',
                'line': line_num,
                'message': 'Bare except clause should specify exception type',
                'severity': 'medium'
            })
        
        # Lambda assignment
        if re.search(r'^\s*\w+\s*=\s*lambda', line):
            issues.append({
                'type': 'style',
                'line': line_num,
                'message': 'Lambda assignment should be replaced with def',
                'severity': 'low'
            })
        
        # Mutable default arguments
        if re.search(r'def\s+\w+\([^)]*=\s*\[\]', line) or re.search(r'def\s+\w+\([^)]*=\s*\{\}', line):
            issues.append({
                'type': 'bug',
                'line': line_num,
                'message': 'Mutable default argument can cause unexpected behavior',
                'severity': 'high'
            })
        
        return issues
    
    def _javascript_specific_checks(self, line_num: int, line: str) -> List[Dict[str, Any]]:
        """JavaScript-specific code quality checks"""
        issues = []
        
        # == instead of ===
        if re.search(r'[^=!]==[^=]', line):
            issues.append({
                'type': 'best-practice',
                'line': line_num,
                'message': 'Use === instead of == for comparison',
                'severity': 'medium'
            })
        
        # var instead of let/const
        if re.search(r'^\s*var\s+', line):
            issues.append({
                'type': 'best-practice',
                'line': line_num,
                'message': 'Use let or const instead of var',
                'severity': 'low'
            })
        
        return issues
    
    def _merge_findings(
        self,
        ai_review: CodeReviewResult,
        security_issues: List[Dict[str, Any]],
        code_smells: List[Dict[str, Any]]
    ) -> CodeReviewResult:
        """Merge AI review with static analysis findings"""
        
        # Convert static analysis issues to review issues
        from .claude_client import ReviewIssue
        
        additional_issues = []
        
        for issue in security_issues + code_smells:
            review_issue = ReviewIssue(
                line=issue.get('line', 0),
                severity=issue.get('severity', 'medium'),
                type=issue.get('type', 'general'),
                message=issue.get('message', ''),
                suggestion=self._get_suggestion_for_issue(issue),
                confidence=0.9  # High confidence for static analysis
            )
            additional_issues.append(review_issue)
        
        # Merge with AI review
        all_issues = ai_review.issues + additional_issues
        
        # Remove duplicates and sort by severity
        unique_issues = self._deduplicate_issues(all_issues)
        
        return CodeReviewResult(
            overall_score=max(1, ai_review.overall_score - len(additional_issues)),
            summary=ai_review.summary,
            issues=unique_issues,
            suggestions=ai_review.suggestions,
            positive_feedback=ai_review.positive_feedback
        )
    
    def _get_suggestion_for_issue(self, issue: Dict[str, Any]) -> str:
        """Get suggestion for static analysis issue"""
        issue_type = issue.get('subtype', issue.get('type', ''))
        
        suggestions = {
            'sql_injection': 'Use parameterized queries or ORM methods',
            'xss': 'Sanitize user input and use safe DOM manipulation methods',
            'path_traversal': 'Validate and sanitize file paths',
            'hardcoded_secrets': 'Use environment variables or secure configuration',
            'long_line': 'Break long lines into multiple lines for better readability',
            'debug_statement': 'Remove debug statements before committing',
            'bare_except': 'Specify the exception type you want to catch',
            'mutable_default': 'Use None as default and create mutable object inside function'
        }
        
        return suggestions.get(issue_type, 'Consider refactoring this code')
    
    def _deduplicate_issues(self, issues: List) -> List:
        """Remove duplicate issues"""
        seen = set()
        unique_issues = []
        
        for issue in issues:
            # Create a key based on line and message
            key = (issue.line, issue.message[:50])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)
        
        # Sort by severity (high -> medium -> low)
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        unique_issues.sort(key=lambda x: severity_order.get(x.severity, 3))
        
        return unique_issues