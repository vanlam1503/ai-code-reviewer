# 🤖 AI Code Reviewer

> **KR3 — Internal AI Initiative #1**  
> Automate team workflows: Code Review + Documentation + Test Suggestion  
> Status: ✅ Completed | Due: 20/06/2026

---

## Tổng quan

**AI Code Reviewer** là một công cụ nội bộ sử dụng **GPT-4o** để tự động hóa ba quy trình trong workflow của team:

| Tính năng | Mô tả |
|-----------|-------|
| 🔍 **AI Code Review** | Phân tích code, phát hiện bug, lỗ hổng bảo mật, vấn đề hiệu suất |
| 📝 **Documentation Generator** | Tự động thêm docstring/comment còn thiếu vào source code |
| 🧪 **Test Suggestion** | Đề xuất các test case cần viết cho từng function/class |
| 🔗 **GitHub PR Integration** | Tự động post review comment vào GitHub Pull Request |
| ⚙️ **GitHub Actions** | Chạy tự động khi có PR mới, không cần thao tác thủ công |

---

## Cấu trúc dự án

```
ai-code-reviewer/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Mẫu cấu hình environment
├── config/
│   └── config.yaml                  # Cấu hình reviewer, filter, threshold
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
│   └── sample_code.py               # Code mẫu để test
└── tests/
    └── test_reviewer.py             # Unit tests (mock OpenAI)
```

---

## Yêu cầu hệ thống

- Python **3.11+**
- Tài khoản [OpenAI](https://platform.openai.com/) với API key
- (Tùy chọn) GitHub Personal Access Token nếu dùng tính năng PR

---

## Cài đặt

### 1. Clone/Copy project

```bash
cd ai-code-reviewer
```

### 2. Tạo virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# hoặc: .venv\Scripts\activate  # Windows
```

### 3. Cài dependencies

```bash
pip install -r requirements.txt
```

### 4. Cấu hình environment

```bash
cp .env.example .env
```

Mở file `.env` và điền:

```env
OPENAI_API_KEY=sk-...your-openai-key...
GITHUB_TOKEN=ghp_...your-github-token...   # chỉ cần cho tính năng PR
```

---

## Hướng dẫn sử dụng

### Lệnh 1: Review file hoặc thư mục

```bash
# Review một file
python main.py review src/my_module.py

# Review toàn bộ thư mục src/
python main.py review src/

# Review nhiều file, lưu report ra thư mục tùy chỉnh
python main.py review src/ tests/ --output ./my-reports

# Review và trả về exit code 1 nếu có lỗi nghiêm trọng (dùng trong CI)
python main.py review src/ --fail-on-issues

# Chọn format report
python main.py review src/ --format markdown   # chỉ Markdown
python main.py review src/ --format json       # chỉ JSON
python main.py review src/ --format both       # cả hai (mặc định)
```

**Kết quả mẫu:**

```
╭─────────────────── Review Result ─────────────────────╮
│ examples/sample_code.py  Score: 48/100  Language: Python │
│ Code has critical security issues requiring immediate fix │
╰────────────────────────────────────────────────────────╯
┌──────────┬──────────┬──────────┬───────────────────────────────┐
│ Severity │ Category │ Location │ Message                       │
├──────────┼──────────┼──────────┼───────────────────────────────┤
│ 🔴 crit  │ security │ L9       │ SQL injection vulnerability    │
│ 🟠 high  │ security │ L5-7     │ MD5 is not suitable for pwd   │
│ 🟡 med   │ style    │ L20      │ Use enumerate instead of len  │
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

### Lệnh 2: Review GitHub Pull Request

```bash
# Review PR #42 trong repo myorg/myrepo và post comment
python main.py pr --owner myorg --repo myrepo --pr 42

# Review nhưng KHÔNG post comment lên GitHub (chỉ xem local)
python main.py pr --owner myorg --repo myrepo --pr 42 --no-post-comment
```

Tool sẽ:
1. Fetch danh sách file thay đổi trong PR
2. Gửi từng diff lên GPT-4o để review
3. Post review comment có bảng issues + suggestions vào PR

---

### Lệnh 3: Tự động generate documentation

```bash
# Xem kết quả tại terminal (không ghi file)
python main.py document src/my_module.py

# Ghi đè file gốc với docstring đã được thêm
python main.py document src/my_module.py --write

# Lưu file đã document vào thư mục khác (không ghi đè gốc)
python main.py document src/ --output-dir ./documented/
```

---

### Demo nhanh với file mẫu

```bash
# Thử review file mẫu có sẵn (có chứa các lỗi cố ý)
python main.py review examples/sample_code.py

# Thử generate documentation cho file mẫu
python main.py document examples/sample_code.py
```

---

## Tích hợp GitHub Actions (CI/CD)

File `.github/workflows/ai-review.yml` đã được cấu hình sẵn.  
Mỗi khi có Pull Request mới hoặc cập nhật, workflow sẽ tự động chạy.

### Bước setup:

1. Vào **GitHub repo → Settings → Secrets and variables → Actions**
2. Thêm secret:
   - `OPENAI_API_KEY` — OpenAI API key của bạn
   - `GITHUB_TOKEN` — tự động có trong GitHub Actions, không cần thêm

3. Push workflow file lên repo:
   ```bash
   git add .github/workflows/ai-review.yml
   git commit -m "feat: add AI code review workflow"
   git push
   ```

4. Tạo một PR bất kỳ — AI review sẽ tự động xuất hiện! 🎉

---

## Cấu hình nâng cao

Chỉnh sửa `config/config.yaml` để tùy chỉnh:

```yaml
reviewer:
  model: "gpt-4o"          # hoặc "gpt-4-turbo", "gpt-3.5-turbo"
  max_file_size_kb: 100    # bỏ qua file lớn hơn ngưỡng này

filters:
  include_extensions:      # chỉ review các loại file này
    - .py
    - .swift
    - .ts
  exclude_paths:           # bỏ qua các path này
    - "tests/*"
    - "**/node_modules/**"

thresholds:
  min_score: 60            # điểm tối thiểu để pass
  block_on_severity: "high"  # REQUEST_CHANGES nếu có issue >= mức này

github:
  review_event: "REQUEST_CHANGES"   # hoặc "COMMENT"
  inline_comments: true
```

---

## Chạy Unit Tests

```bash
# Chạy toàn bộ test suite (không cần OpenAI API key — dùng mock)
python -m pytest tests/ -v

# Kết quả mong đợi:
# tests/test_reviewer.py::TestDetectLanguage::test_python PASSED
# tests/test_reviewer.py::TestDetectLanguage::test_typescript PASSED
# tests/test_reviewer.py::TestAICodeReviewer::test_review_returns_result PASSED
# tests/test_reviewer.py::TestReportGenerator::test_render_markdown_contains_filename PASSED
# ... (10 tests total)
```

---

## Chi phí ước tính (OpenAI API)

| Kịch bản | Token ước tính | Chi phí (GPT-4o) |
|----------|----------------|------------------|
| Review 1 file ~200 dòng | ~2,000 tokens | ~$0.01 |
| PR với 5 file thay đổi | ~10,000 tokens | ~$0.05 |
| Review toàn bộ project nhỏ (~20 files) | ~40,000 tokens | ~$0.20 |

> Sử dụng `gpt-3.5-turbo` trong config để giảm chi phí ~10x (ít chính xác hơn).

---

## Kiến trúc hệ thống

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

## Tham khảo & Nguồn cảm hứng

| Tool | Link | Đóng góp |
|------|------|----------|
| **Danger** | [github.com/danger/danger](https://github.com/danger/danger) | Ý tưởng automated PR checks |
| **SwiftLint** | [github.com/realm/SwiftLint](https://github.com/realm/SwiftLint) | Pattern phân tích style/convention |
| **Sourcegraph Cody** | [github.com/sourcegraph/cody](https://github.com/sourcegraph/cody) | AI-assisted code understanding |
| **SwiftFormat** | [github.com/nicklockwood/SwiftFormat](https://github.com/nicklockwood/SwiftFormat) | Code formatting automation |

---

## License

MIT — Internal use only.  
*Developed as part of KR3: Internal AI Initiative #1*
