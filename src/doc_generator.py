"""
AI Documentation Generator Module
Automatically generates or improves docstrings and module-level documentation.
"""

import ast
import os
from dataclasses import dataclass
from typing import Optional

import openai


@dataclass
class DocResult:
    filename: str
    original_code: str
    documented_code: str
    added_docstrings: int
    summary: str


DOC_SYSTEM_PROMPT = """You are an expert technical writer and software engineer.
Given source code, add or improve docstrings/comments following best practices
for the detected language (Google-style for Python, JSDoc for JS/TS, etc.).

Rules:
- Add module-level docstrings if missing
- Add class and function/method docstrings that describe purpose, params, and return values
- Keep existing code logic EXACTLY unchanged — only add/update documentation
- Return ONLY the fully documented source code, no extra commentary or markdown fences."""


class DocGenerator:
    """Generates docstrings and documentation using GPT-4o."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.client = openai.OpenAI(
            api_key=api_key or os.environ["OPENAI_API_KEY"]
        )
        self.model = model

    def generate_docs(self, code: str, filename: str) -> DocResult:
        """Add missing docstrings to source code using AI."""
        _, ext = os.path.splitext(filename)
        lang = ext.lstrip(".") or "python"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DOC_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"File: {filename}\n"
                        f"Language: {lang}\n\n"
                        f"{code}"
                    ),
                },
            ],
            temperature=0.1,
        )

        documented_code = response.choices[0].message.content.strip()

        # Count added docstrings (Python-specific heuristic)
        added = 0
        if ext == ".py":
            added = _count_new_docstrings(code, documented_code)

        return DocResult(
            filename=filename,
            original_code=code,
            documented_code=documented_code,
            added_docstrings=added,
            summary=f"Added/improved {added} docstring(s) in {filename}",
        )

    def generate_readme_section(self, code: str, filename: str) -> str:
        """Generate a README section describing a module."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a technical writer. Given source code, write a concise "
                        "Markdown section (heading + 2-3 paragraphs) suitable for a README. "
                        "Include: purpose, key classes/functions, and usage example."
                    ),
                },
                {"role": "user", "content": f"File: {filename}\n\n{code}"},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _count_new_docstrings(original: str, documented: str) -> int:
    """Count how many new triple-quoted strings were added (Python)."""
    def _docstring_count(src: str) -> int:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return src.count('"""') // 2 + src.count("'''") // 2
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    count += 1
        return count

    original_count = _docstring_count(original)
    documented_count = _docstring_count(documented)
    return max(0, documented_count - original_count)
