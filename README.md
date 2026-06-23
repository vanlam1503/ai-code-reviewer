# 🤖 AI Code Reviewer

> **KR3 — Internal AI Initiative #1**
> Automate team workflows: Code Review + Documentation + Test Suggestion
> Status: ✅ Completed | Due: 20/06/2026

---

## Overview

**AI Code Reviewer** is an internal tool using **GPT-4o** to automate three team workflows:

| Feature | Description |
|---------|-------------|
| 🔍 **AI Code Review** | Analyze code to find bugs, security vulnerabilities, and performance issues |
| 📝 **Documentation Generator** | Automatically add missing docstrings/comments to source code |
| 🧪 **Test Suggestion** | Recommend test cases to write for each function/class |
| 🔗 **GitHub PR Integration** | Automatically post review comments to GitHub Pull Requests |
| ⚙️ **GitHub Actions** | Run automatically on new PRs without manual steps |

---

## Project Structure

```
ai-code-reviewer/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Example environment configuration
├── config/
│   └── config.yaml                  # Reviewer configuration, filters, thresholds
├── src/
│   ├── __init__.py
│   ├── code_reviewer.py             # Core: AI review logic (GPT-4o)
│   ├── github_integration.py        # GitHub REST API client + report builder
│   ├── doc_generator.py             # AI documentation generator
│   └── report_generator.py          # Render Markdown / JSON reports
├── .github/
│   └── workflows/
│       └── ai-review.yml            # GitHub Actions workflow
├── examples/
│   └── sample_code.py               # Sample code for testing
└── tests/
    └── test_reviewer.py             # Unit tests (mock OpenAI)
```

---

## System Requirements

- Python **3.11+**
- An [OpenAI](https://platform.openai.com/) account with an API key
- (Optional) GitHub Personal Access Token if you use the PR features

---

## Installation

### 1. Clone / enter the project directory

```bash
cd ai-code-reviewer
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# or: .venv\Scripts\activate  # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
OPENAI_API_KEY=sk-...your-openai-key...
GITHUB_TOKEN=ghp_...your-github-token...   # only needed for PR posting
```

---

## Usage

### Command 1: Review a file or directory

```bash
# Review a single file
python main.py review src/my_module.py

# Review the entire src/ directory
python main.py review src/

# Review multiple paths and save reports to a custom folder
python main.py review src/ tests/ --output ./my-reports

# Return exit code 1 if there are severe issues (useful in CI)
python main.py review src/ --fail-on-issues

# Choose report format
python main.py review src/ --format markdown   # markdown only
python main.py review src/ --format json       # json only
python main.py review src/ --format both       # both (default)
```

Sample output:

```
╭─────────────────── Review Result ─────────────────────╮
│ examples/sample_code.py  Score: 48/100  Language: Python │
│ Code has critical security issues requiring immediate fix │
╰────────────────────────────────────────────────────────╯
┌──────────┬──────────┬──────────┬───────────────────────────────┐
│ Severity │ Category │ Location │ Message                       │
├──────────┼──────────┼──────────┼───────────────────────────────┤
│ 🔴 crit  │ security │ L9       │ SQL injection vulnerability    │
│ 🟠 high  │ security │ L5-7     │ MD5 is not suitable for pwd    │
│ 🟡 med   │ style    │ L20      │ Use enumerate instead of len   │
└──────────┴──────────┴──────────┴───────────────────────────────┘

🧪 Test Suggestions:
  • Test divide() with b=0 to check ZeroDivisionError
  • Test transform() with rows containing fewer than 2 columns

📝 Documentation Gaps:
  • Add module-level docstring explaining purpose
  • Document DataProcessor class and its public methods

✅ Markdown report saved: ./reports/review_report.md
✅ JSON report saved: ./reports/review_report.json
```

---

### Command 2: Review a GitHub Pull Request

```bash
# Review PR #42 in repo myorg/myrepo and post comments
python main.py pr --owner myorg --repo myrepo --pr 42

# Review but DO NOT post comments to GitHub (local only)
python main.py pr --owner myorg --repo myrepo --pr 42 --no-post-comment
```

The tool will:
1. Fetch the list of changed files in the PR
2. Send each diff to GPT-4o for review
3. Post a review comment with a table of issues + suggestions to the PR

---

### Command 3: Automatically generate documentation

```bash
# Print results to terminal (do not overwrite files)
python main.py document src/my_module.py

# Overwrite the original file with added docstrings
python main.py document src/my_module.py --write

# Save documented files to a different folder (do not overwrite originals)
python main.py document src/ --output-dir ./documented/
```

---

### Quick demo with the sample file

```bash
# Try reviewing the provided sample file (contains intentional issues)
python main.py review examples/sample_code.py

# Try generating documentation for the sample file
python main.py document examples/sample_code.py
```

---

## GitHub Actions Integration (CI/CD)

The `.github/workflows/ai-review.yml` workflow is preconfigured.
It runs automatically whenever a Pull Request is opened or updated.

### Setup steps:

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add the following secret(s):
   - `OPENAI_API_KEY` — your OpenAI API key
   - `GITHUB_TOKEN` — automatically available in GitHub Actions, no need to add

3. Push the workflow file to the repo:
   ```bash
   git add .github/workflows/ai-review.yml
   git commit -m "feat: add AI code review workflow"
   git push
   ```

4. Open any PR — the AI review will run automatically! 🎉

---

## Advanced Configuration

Edit `config/config.yaml` to customize behavior:

```yaml
reviewer:
  model: "gpt-4o"          # or "gpt-4-turbo", "gpt-3.5-turbo"
  max_file_size_kb: 100     # skip files larger than this threshold

filters:
  include_extensions:       # only review these file extensions
    - .py
    - .swift
    - .ts
  exclude_paths:            # skip these paths
    - "tests/*"
    - "**/node_modules/**"

thresholds:
  min_score: 60             # minimum score to pass
  block_on_severity: "high"  # REQUEST_CHANGES if any issue >= this severity

github:
  review_event: "REQUEST_CHANGES"   # or "COMMENT"
  inline_comments: true
```

---

## Running Unit Tests

```bash
# Run the full test suite (no OpenAI API key required — uses mocks)
python -m pytest tests/ -v

# Expected results:
# tests/test_reviewer.py::TestDetectLanguage::test_python PASSED
# tests/test_reviewer.py::TestDetectLanguage::test_typescript PASSED
# tests/test_reviewer.py::TestAICodeReviewer::test_review_returns_result PASSED
# tests/test_reviewer.py::TestReportGenerator::test_render_markdown_contains_filename PASSED
# ... (10 tests total)
```

---

## Estimated Cost (OpenAI API)

| Scenario | Estimated tokens | Cost (GPT-4o) |
|---------|------------------:|---------------:|
| Review 1 file (~200 lines) | ~2,000 tokens | ~$0.01 |
| PR with 5 changed files     | ~10,000 tokens | ~$0.05 |
| Review a small project (~20 files) | ~40,000 tokens | ~$0.20 |

> Use `gpt-3.5-turbo` in the config to reduce costs by ~10x (less accurate).

---

## System Architecture

```
Developer opens PR
       │
       ▼
GitHub Actions triggers
       │
       ▼
main.py pr command
       │
       ├─► GitHubClient.get_pr_files()  ──► GitHub REST API
       │
       ├─► AICodeReviewer.review_diff()  ──► OpenAI GPT-4o API
       │         │
       │         └─► ReviewResult (score, comments, test/doc suggestions)
       │
       ├─► build_review_markdown()  ──► Formatted Markdown comment
       │
       └─► GitHubClient.post_review()  ──► PR Review Comment on GitHub
```

---

## References & Inspiration

| Tool | Link | Contribution |
|------|------|--------------|
| **Danger** | [github.com/danger/danger](https://github.com/danger/danger) | Idea for automated PR checks |
| **SwiftLint** | [github.com/realm/SwiftLint](https://github.com/realm/SwiftLint) | Style/convention analysis patterns |
| **Sourcegraph Cody** | [github.com/sourcegraph/cody](https://github.com/sourcegraph/cody) | AI-assisted code understanding |
| **SwiftFormat** | [github.com/nicklockwood/SwiftFormat](https://github.com/nicklockwood/SwiftFormat) | Code formatting automation |

---

## License

MIT — Internal use only.
*Developed as part of KR3: Internal AI Initiative #1*
