"""Unit tests for the AI Code Reviewer (uses mocked OpenAI responses)."""

import json
import unittest
from unittest.mock import MagicMock, patch

from src.code_reviewer import AICodeReviewer, ReviewResult, ReviewComment, Severity, detect_language
from src.report_generator import render_markdown, render_json
from src.doc_generator import _count_new_docstrings


# ------------------------------------------------------------------
# detect_language
# ------------------------------------------------------------------

class TestDetectLanguage(unittest.TestCase):
    def test_python(self):
        self.assertEqual(detect_language("foo.py"), "Python")

    def test_typescript(self):
        self.assertEqual(detect_language("app.ts"), "TypeScript")

    def test_swift(self):
        self.assertEqual(detect_language("View.swift"), "Swift")

    def test_unknown(self):
        self.assertEqual(detect_language("Makefile"), "Unknown")


# ------------------------------------------------------------------
# AICodeReviewer (mocked)
# ------------------------------------------------------------------

MOCK_GPT_RESPONSE = {
    "overall_score": 72,
    "summary": "Code is functional but has security and style issues.",
    "comments": [
        {
            "severity": "high",
            "category": "security",
            "line_range": "5-7",
            "message": "MD5 is not suitable for password hashing.",
            "suggestion": "Use bcrypt or argon2 instead.",
        },
        {
            "severity": "critical",
            "category": "security",
            "line_range": "9",
            "message": "SQL injection vulnerability.",
            "suggestion": "Use parameterized queries.",
        },
    ],
    "test_suggestions": ["Test divide() with b=0", "Test transform() with malformed CSV"],
    "doc_suggestions": ["Add docstrings to all public functions", "Document DataProcessor class purpose"],
}


class TestAICodeReviewer(unittest.TestCase):
    def _make_mock_client(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(MOCK_GPT_RESPONSE)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @patch("src.code_reviewer.openai.OpenAI")
    def test_review_returns_result(self, mock_openai_cls):
        mock_openai_cls.return_value = self._make_mock_client()
        reviewer = AICodeReviewer(api_key="test-key")
        result = reviewer.review_code("def foo(): pass", "foo.py")

        self.assertIsInstance(result, ReviewResult)
        self.assertEqual(result.filename, "foo.py")
        self.assertEqual(result.language, "Python")
        self.assertEqual(result.overall_score, 72)
        self.assertEqual(len(result.comments), 2)

    @patch("src.code_reviewer.openai.OpenAI")
    def test_review_passed_is_false_when_high_severity(self, mock_openai_cls):
        mock_openai_cls.return_value = self._make_mock_client()
        reviewer = AICodeReviewer(api_key="test-key")
        result = reviewer.review_code("x = 1", "x.py")
        self.assertFalse(result.passed)

    @patch("src.code_reviewer.openai.OpenAI")
    def test_review_diff(self, mock_openai_cls):
        mock_openai_cls.return_value = self._make_mock_client()
        reviewer = AICodeReviewer(api_key="test-key")
        diff = "+def new_func():\n+    pass\n-old_line\n"
        result = reviewer.review_diff(diff, "foo.py")
        self.assertIsNotNone(result)


# ------------------------------------------------------------------
# Report Generator
# ------------------------------------------------------------------

class TestReportGenerator(unittest.TestCase):
    def _make_result(self):
        return ReviewResult(
            filename="foo.py",
            language="Python",
            overall_score=85,
            summary="Looks good overall.",
            comments=[
                ReviewComment(
                    severity=Severity.MEDIUM,
                    category="style",
                    line_range="3",
                    message="Use enumerate instead of range(len()).",
                    suggestion="for i, item in enumerate(items):",
                )
            ],
            test_suggestions=["Test edge case X"],
            doc_suggestions=["Add module docstring"],
        )

    def test_render_markdown_contains_filename(self):
        result = self._make_result()
        md = render_markdown([result])
        self.assertIn("foo.py", md)
        self.assertIn("85/100", md)

    def test_render_json_valid(self):
        result = self._make_result()
        js = render_json([result])
        data = json.loads(js)
        self.assertEqual(data["summary"]["files_reviewed"], 1)
        self.assertEqual(data["results"][0]["overall_score"], 85)


# ------------------------------------------------------------------
# DocGenerator helpers
# ------------------------------------------------------------------

class TestDocGeneratorHelpers(unittest.TestCase):
    def test_count_new_docstrings(self):
        original = "def foo():\n    pass\n"
        documented = 'def foo():\n    """Do foo."""\n    pass\n'
        count = _count_new_docstrings(original, documented)
        self.assertEqual(count, 1)

    def test_no_new_docstrings(self):
        code = 'def foo():\n    """Already documented."""\n    pass\n'
        count = _count_new_docstrings(code, code)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
