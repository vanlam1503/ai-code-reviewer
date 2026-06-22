"""
Report Generator Module
Renders HTML and Markdown reports from review results.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.code_reviewer import ReviewResult, Severity


# ------------------------------------------------------------------
# Markdown Report
# ------------------------------------------------------------------

SEVERITY_EMOJI = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🔵",
    Severity.INFO: "⚪",
}


def render_markdown(results: list[ReviewResult], title: str = "AI Code Review Report") -> str:
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# {title}",
        f"*Generated: {now}*\n",
        "---\n",
    ]

    total_issues = sum(len(r.comments) for r in results)
    avg_score = int(sum(r.overall_score for r in results) / len(results)) if results else 0
    passed = sum(1 for r in results if r.passed)

    lines += [
        "## Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Files reviewed | {len(results)} |",
        f"| Average score | {avg_score}/100 |",
        f"| Files passed | {passed}/{len(results)} |",
        f"| Total issues | {total_issues} |",
        "",
    ]

    for result in results:
        score_bar = "█" * (result.overall_score // 10) + "░" * (10 - result.overall_score // 10)
        status = "✅ PASSED" if result.passed else "❌ NEEDS CHANGES"
        lines += [
            f"## `{result.filename}`  {status}",
            f"**Score:** {result.overall_score}/100 `{score_bar}`  |  **Language:** {result.language}",
            f"> {result.summary}",
            "",
        ]

        if result.comments:
            lines += [
                "### Issues",
                "| # | Severity | Category | Location | Message | Suggestion |",
                "|---|----------|----------|----------|---------|------------|",
            ]
            for i, c in enumerate(result.comments, 1):
                emoji = SEVERITY_EMOJI.get(c.severity, "")
                loc = f"L{c.line_range}" if c.line_range else "—"
                suggestion = (c.suggestion or "—").replace("\n", " ")
                lines.append(
                    f"| {i} | {emoji} {c.severity.value} | {c.category} | {loc} | {c.message} | {suggestion} |"
                )
            lines.append("")

        if result.test_suggestions:
            lines.append("### 🧪 Test Suggestions")
            for t in result.test_suggestions:
                lines.append(f"- {t}")
            lines.append("")

        if result.doc_suggestions:
            lines.append("### 📝 Documentation Gaps")
            for d in result.doc_suggestions:
                lines.append(f"- {d}")
            lines.append("")

        lines.append("---\n")

    lines.append("*Powered by [AI Code Reviewer](https://github.com/your-org/ai-code-reviewer) · GPT-4o*")
    return "\n".join(lines)


# ------------------------------------------------------------------
# JSON Report
# ------------------------------------------------------------------

def render_json(results: list[ReviewResult]) -> str:
    data = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "summary": {
            "files_reviewed": len(results),
            "average_score": int(sum(r.overall_score for r in results) / len(results)) if results else 0,
            "passed": sum(1 for r in results if r.passed),
            "total_issues": sum(len(r.comments) for r in results),
        },
        "results": [
            {
                "filename": r.filename,
                "language": r.language,
                "overall_score": r.overall_score,
                "passed": r.passed,
                "summary": r.summary,
                "comments": [
                    {
                        "severity": c.severity.value,
                        "category": c.category,
                        "line_range": c.line_range,
                        "message": c.message,
                        "suggestion": c.suggestion,
                    }
                    for c in r.comments
                ],
                "test_suggestions": r.test_suggestions,
                "doc_suggestions": r.doc_suggestions,
            }
            for r in results
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------
# Save helpers
# ------------------------------------------------------------------

def save_report(content: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
