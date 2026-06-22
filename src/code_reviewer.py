"""
Core AI Code Reviewer Module
Uses OpenAI GPT-4 to analyze code for quality, bugs, security, and best practices.
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import openai


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ReviewComment:
    severity: Severity
    category: str          # "bug", "security", "performance", "style", "documentation"
    line_range: Optional[str]
    message: str
    suggestion: Optional[str] = None


@dataclass
class ReviewResult:
    filename: str
    language: str
    overall_score: int     # 0-100
    summary: str
    comments: list[ReviewComment] = field(default_factory=list)
    test_suggestions: list[str] = field(default_factory=list)
    doc_suggestions: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True if no critical/high severity issues found."""
        return not any(
            c.severity in (Severity.CRITICAL, Severity.HIGH)
            for c in self.comments
        )


REVIEW_SYSTEM_PROMPT = """You are an expert code reviewer with deep knowledge of software engineering best practices.
Analyze the provided code and return a JSON response with:

{
  "overall_score": <int 0-100>,
  "summary": "<brief overall assessment>",
  "comments": [
    {
      "severity": "<critical|high|medium|low|info>",
      "category": "<bug|security|performance|style|documentation>",
      "line_range": "<e.g. '12-15' or null>",
      "message": "<specific issue description>",
      "suggestion": "<concrete fix or improvement>"
    }
  ],
  "test_suggestions": ["<test case descriptions>"],
  "doc_suggestions": ["<missing or unclear documentation items>"]
}

Focus on:
- Bugs and logical errors
- Security vulnerabilities (OWASP Top 10 awareness)
- Performance bottlenecks
- Code style and readability
- Missing tests and documentation
Return ONLY valid JSON, no markdown fences."""


def detect_language(filename: str) -> str:
    ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".swift": "Swift", ".kt": "Kotlin", ".java": "Java",
        ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".cs": "C#",
        ".cpp": "C++", ".c": "C", ".php": "PHP",
    }
    _, ext = os.path.splitext(filename)
    return ext_map.get(ext.lower(), "Unknown")


class AICodeReviewer:
    """AI-powered code reviewer using OpenAI GPT-4."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.client = openai.OpenAI(
            api_key=api_key or os.environ["OPENAI_API_KEY"]
        )
        self.model = model

    def review_code(self, code: str, filename: str) -> ReviewResult:
        """Submit code to GPT-4 for review and return a structured ReviewResult."""
        import json

        language = detect_language(filename)
        user_prompt = (
            f"File: {filename}\n"
            f"Language: {language}\n\n"
            f"```{language.lower()}\n{code}\n```"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)

        comments = [
            ReviewComment(
                severity=Severity(c["severity"]),
                category=c["category"],
                line_range=c.get("line_range"),
                message=c["message"],
                suggestion=c.get("suggestion"),
            )
            for c in data.get("comments", [])
        ]

        return ReviewResult(
            filename=filename,
            language=language,
            overall_score=data.get("overall_score", 0),
            summary=data.get("summary", ""),
            comments=comments,
            test_suggestions=data.get("test_suggestions", []),
            doc_suggestions=data.get("doc_suggestions", []),
        )

    def review_diff(self, diff: str, filename: str) -> ReviewResult:
        """Review only the changed lines from a git diff."""
        added_lines = "\n".join(
            line[1:] for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        return self.review_code(added_lines, filename)
