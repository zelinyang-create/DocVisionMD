# pdf_vlm_md

A PDF-to-Markdown converter powered by a Vision Language Model (VLM). Instead of relying on traditional OCR or text extraction, it renders each PDF page as a high-resolution image and sends it to a VLM, which reconstructs the full page content — text, headings, tables, figures, and layout — as structured Markdown.

Designed for complex technical documents (engineering specs, process regulations, multi-level tables with merged cells) where layout fidelity matters.

---

## How It Works

Conversion runs in two sequential phases, both using the same VLM:

**Phase 1 — Structure Extraction (serial)**
Each page image is sent to the VLM with a lightweight prompt that asks only for structural metadata: heading texts and levels, table titles, whether the page is a TOC page, and whether it continues a table from the previous page. This produces a `DocumentContext` that the next phase uses to anchor heading levels across all pages.

**Phase 2 — Markdown Conversion (parallel)**
Each page is converted independently and concurrently. The VLM receives the page image plus the Phase 1 context for that page (known headings, heading stack, previous page tail) and outputs the full Markdown for that page. Pages are then concatenated in order.

**Postprocessing**
A deterministic rule-based pipeline cleans up the joined Markdown: heading level normalization, TOC block formatting, header/footer deduplication across pages, appendix heading promotion, table title promotion, figure caption demotion, flowchart section handling, and table repair (closing unclosed HTML tags, fixing tables with a missing header row).

```
PDF
 │
 ▼
[Render pages to PNG at 600 DPI]  ← PyMuPDF
 │
 ▼
[Phase 1] Structural outline per page  ← VLM (serial)
 │
 ▼
[Phase 2] Full Markdown per page       ← VLM (parallel, up to 16 workers)
 │
 ▼
[Postprocessing] Cleanup & normalization
 │
 ▼
output.md
```

---

## Table Handling

Tables are a first-class concern. The VLM is instructed to apply a two-path rule:

- **Simple tables** (no merged cells) → standard Markdown `|` pipe syntax
- **Complex tables** (any `colspan` or `rowspan`) → HTML `<table>` with explicit `colspan="N"` / `rowspan="N"` attributes

The postprocessor repairs common VLM slip-ups: unclosed `<table>` tags that would corrupt surrounding content, and Markdown tables where the separator row (`| :--- |`) was emitted as the first row with no header above it.

---

## Installation

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

| Dependency | Purpose |
|---|---|
| `PyMuPDF` | Render PDF pages to PNG images |
| `openai` | VLM API calls (OpenAI-compatible interface) |
| `python-dotenv` | Load config from `.env` |
| `click` | CLI framework |
| `pillow` | Image handling |
| `pytest` | Test runner |

---

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `QWEN_API_KEY` | ✅ | — | API key for your VLM provider |
| `QWEN_API_BASE` | ✅ | — | OpenAI-compatible base URL (e.g. DashScope) |
| `QWEN_MODEL` | ✅ | — | Model name for Phase 2 (full page conversion) |
| `QWEN_OUTLINE_MODEL` | | same as `QWEN_MODEL` | Model name for Phase 1 (structure extraction only) |
| `QWEN_ENABLE_THINKING` | | `false` | Enable extended thinking / chain-of-thought if supported |
| `QWEN_TEMPERATURE` | | `0` | Sampling temperature (lower = more deterministic) |
| `QWEN_TOP_P` | | `0.1` | Top-p sampling |
| `QWEN_MAX_TOKENS` | | `8192` | Max tokens per VLM response |
| `PDF_RENDER_DPI` | | `600` | DPI for page image rendering (higher = sharper, slower) |
| `MAX_PREVIOUS_TAIL_CHARS` | | `300` | Characters from the previous page passed as context to the next |
| `PYMUPDF_TEXT_MIN_CHARS` | | `50` | Min characters for a page to be considered text-extractable by PyMuPDF |
| `PYMUPDF_STRUCTURE_CONFIDENCE_MIN` | | `0.45` | Confidence threshold for PyMuPDF-based structure fallback |
| `PHASE2_MAX_WORKERS` | | `16` | Max concurrent Phase 2 VLM calls |

The tool is tested with **Alibaba Cloud DashScope** (`qwen-vl-max` / `qwen3.6-plus`), but any OpenAI-compatible API that accepts image inputs should work (GPT-4o, Gemini via proxy, etc.).

---

## Usage

```bash
# Basic conversion
python -m pdf_vlm_md convert report.pdf -o report.md

# Verbose logging
python -m pdf_vlm_md -v convert report.pdf -o report.md

# Debug mode: saves page images and Phase 1 JSON to _debug/
python -m pdf_vlm_md convert report.pdf -o report.md --debug
```

The output is a single self-contained Markdown file. Page boundary comments (`<!-- page: N -->`) are stripped from the final output unless `--debug` is set.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

The test suite covers postprocessing functions (heading normalization, TOC handling, table repair, appendix promotion, redaction stripping, etc.) and prompt content assertions. It does not make live VLM API calls.

---

## Project Structure

```
pdf_vlm_md/
├── __main__.py         # Entry point: python -m pdf_vlm_md
├── cli.py              # Click CLI definitions
├── convert.py          # Top-level orchestrator: Phase 1 → Phase 2 → postprocess
├── outline.py          # Phase 1: per-page structure extraction via VLM
├── convert_page.py     # Phase 2: per-page Markdown conversion via VLM
├── postprocess.py      # Rule-based postprocessing pipeline (15+ passes)
├── prompts.py          # System prompts for Phase 1 and Phase 2
├── models.py           # Dataclasses: DocumentContext, PageContext, Heading, etc.
├── config.py           # Environment variable loading
├── pdf_extractor.py    # PDF page rendering to PIL images (PyMuPDF)
├── qwen_client.py      # VLM API client wrapper
├── heading_rules.py    # Regex rules for heading/table title detection
├── structure_enrich.py # Flowchart section and heading stack logic
├── utils.py            # Shared utilities
└── validators.py       # Output validation helpers

tests/
├── conftest.py
├── test_postprocess_integration.py
├── test_postprocess_table_repair.py   # HTML close repair + MD header fix
├── test_prompt_table_rules.py         # Prompt content assertions
├── test_heading_levels.py
├── test_toc_normalization.py
├── test_appendix_levels.py
├── test_table_title_demotion.py
├── test_promote_plain_headings.py
├── test_redaction_and_table_headings.py
└── ...

docs/superpowers/
├── specs/    # Design documents
└── plans/    # Implementation plans
```

---

## Known Limitations

- **Extremely complex tables** (13+ columns, multi-level merged headers spanning many rows) may still be emitted as Markdown by the VLM despite HTML instructions, resulting in column-count mismatches. These cases require manual review.
- **Multi-page tables**: each page is a separate VLM call with no shared state, so the VLM cannot always infer the correct column structure for continuation pages that lack a visible header.
- **Handwritten or low-quality scans**: recognized content is wrapped in `<NOTSURE>` tags; heavily degraded pages get a quality warning comment.
- **Non-text pages** (full-page figures, flowcharts): converted to a structured text description rather than the original visual layout.
