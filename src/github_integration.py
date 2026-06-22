"""
GitHub Integration Module
Fetches PR diffs and posts AI review comments back to GitHub Pull Requests.
"""

import os
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class PullRequestFile:
    filename: str
    patch: str          # raw unified diff
    additions: int
    deletions: int
    status: str         # added, modified, removed


class GitHubClient:
    """
    Thin GitHub REST API client for PR review automation.
    Uses a Personal Access Token (PAT) or GitHub Actions GITHUB_TOKEN.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ["GITHUB_TOKEN"]
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    # ------------------------------------------------------------------
    # Fetch PR data
    # ------------------------------------------------------------------

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[PullRequestFile]:
        """Return list of files changed in a PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        resp = self.session.get(url)
        resp.raise_for_status()

        files = []
        for item in resp.json():
            patch = item.get("patch", "")          # patch may be absent for binary files
            if patch:
                files.append(PullRequestFile(
                    filename=item["filename"],
                    patch=patch,
                    additions=item["additions"],
                    deletions=item["deletions"],
                    status=item["status"],
                ))
        return files

    def get_pr_head_sha(self, owner: str, repo: str, pr_number: int) -> str:
        """Return the HEAD commit SHA of the PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()["head"]["sha"]

    # ------------------------------------------------------------------
    # Post review
    # ------------------------------------------------------------------

    def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        body: str,
        event: str = "COMMENT",   # APPROVE | REQUEST_CHANGES | COMMENT
        inline_comments: Optional[list[dict]] = None,
    ) -> dict:
        """
        Submit a PR review with an optional top-level body and inline comments.

        inline_comments format:
          [{"path": "src/foo.py", "line": 42, "body": "Issue text"}]
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        payload: dict = {
            "commit_id": commit_sha,
            "body": body,
            "event": event,
        }
        if inline_comments:
            payload["comments"] = [
                {
                    "path": c["path"],
                    "line": c["line"],
                    "body": c["body"],
                    "side": "RIGHT",
                }
                for c in inline_comments
            ]

        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    def post_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> dict:
        """Post a plain issue comment on a PR (not an inline review comment)."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        resp = self.session.post(url, json={"body": body})
        resp.raise_for_status()
        return resp.json()


# ------------------------------------------------------------------
# Helper: build Markdown review body from ReviewResult list
# ------------------------------------------------------------------

def build_review_markdown(results: list) -> str:
    """Convert a list of ReviewResult objects into a Markdown PR comment."""
    from src.code_reviewer import Severity

    SEVERITY_EMOJI = {
        Severity.CRITICAL: "🔴",
        Severity.HIGH: "🟠",
        Severity.MEDIUM: "🟡",
        Severity.LOW: "🔵",
        Severity.INFO: "⚪",
    }

    lines = ["## 🤖 AI Code Review Report\n"]

    all_passed = all(r.passed for r in results)
    lines.append(f"**Overall status:** {'✅ Passed' if all_passed else '❌ Needs Changes'}\n")
    lines.append("---\n")

    for result in results:
        score_bar = "█" * (result.overall_score // 10) + "░" * (10 - result.overall_score // 10)
        lines.append(f"### 📄 `{result.filename}` — Score: {result.overall_score}/100 `{score_bar}`")
        lines.append(f"> {result.summary}\n")

        if result.comments:
            lines.append("#### Issues Found\n")
            lines.append("| Severity | Category | Location | Message |")
            lines.append("|----------|----------|----------|---------|")
            for c in result.comments:
                emoji = SEVERITY_EMOJI.get(c.severity, "")
                loc = f"L{c.line_range}" if c.line_range else "—"
                lines.append(f"| {emoji} {c.severity.value} | {c.category} | {loc} | {c.message} |")
            lines.append("")

            for c in result.comments:
                if c.suggestion:
                    lines.append(f"**💡 Suggestion for `{c.category}`:** {c.suggestion}\n")

        if result.test_suggestions:
            lines.append("#### 🧪 Suggested Tests")
            for t in result.test_suggestions:
                lines.append(f"- {t}")
            lines.append("")

        if result.doc_suggestions:
            lines.append("#### 📝 Documentation Gaps")
            for d in result.doc_suggestions:
                lines.append(f"- {d}")
            lines.append("")

        lines.append("---\n")

    lines.append("*Generated by [AI Code Reviewer](https://github.com/your-org/ai-code-reviewer) · Powered by GPT-4o*")
    return "\n".join(lines)
