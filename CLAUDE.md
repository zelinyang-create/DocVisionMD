# CLAUDE.md — pdf_vlm_md

## Language

Always respond in Chinese (中文). Never switch to Korean or any other language.

## Project Overview

PDF-to-Markdown converter using a Vision Language Model (VLM). Each PDF page is rendered as a PNG image and sent to the VLM, which outputs structured Markdown. Processing flow: Phase 1 (serial structure extraction) → Phase 1.5 heading releveling → Phase 2 (parallel per-page conversion) → postprocessing.

Entry point: `python -m pdf_vlm_md convert <input.pdf> -o <output.md>`

## Key Files

| File | Role |
|---|---|
| `pdf_vlm_md/convert.py` | Top-level orchestrator |
| `pdf_vlm_md/outline.py` | Phase 1: structural metadata per page |
| `pdf_vlm_md/convert_page.py` | Phase 2: full Markdown per page |
| `pdf_vlm_md/postprocess.py` | ~15-pass deterministic cleanup pipeline |
| `pdf_vlm_md/prompts.py` | System prompts for Phase 1 and Phase 2 |
| `pdf_vlm_md/models.py` | Dataclasses: DocumentContext, PageContext, Heading |
| `pdf_vlm_md/config.py` | Env var loading via `get_config()` |
| `pdf_vlm_md/pdf_extractor.py` | PDF page rendering to PIL images (PyMuPDF) |
| `pdf_vlm_md/qwen_client.py` | VLM API client wrapper |
| `pdf_vlm_md/heading_rules.py` | Regex rules for heading/table title detection |
| `pdf_vlm_md/structure_enrich.py` | Flowchart section and heading stack logic |

## Configuration

Copy `.env.example` to `.env` and fill in credentials. **Never commit `.env`** — it contains a real API key.

Key env vars:
- `QWEN_API_KEY` — required
- `QWEN_API_BASE` — required (DashScope: `https://dashscope.aliyuncs.com/compatible-mode/v1`)
- `QWEN_MODEL` — default `qwen3.6-plus`
- `QWEN_OUTLINE_MODEL` — defaults to `QWEN_MODEL`
- `PDF_RENDER_DPI` — default `600`
- `PHASE2_MAX_WORKERS` — default `16`

## Running Tests

```bash
python -m pytest tests/ -v
# Skip the pre-existing broken test (AttributeError on choose_extraction_method):
python -m pytest tests/ -v --ignore=tests/test_phase1_fallback.py
```

Tests do not make live VLM API calls.

## Table Handling (Critical)

Document tables are emitted as HTML:
- All document tables → HTML `<table>` syntax
- Merged cells use explicit `colspan` / `rowspan` attributes
- Markdown pipe tables are reserved for generated helper structures such as flowchart node lists

Postprocessing repairs:
- `repair_unclosed_html_tables()` — closes `<table>` tags missing `</table>` within each page block
- `deduplicate_headers_footers()` — keeps table structure lines while removing repeated headers/footers

## Page Boundary Markers

Pages are separated by `<!-- page: N -->` comments during processing. The postprocessor uses these as boundaries for repairs. They are stripped from the final output unless `--debug` is set.

## Development Conventions

- Follow TDD: write failing tests first, then implement
- Use `docs/superpowers/plans/` for implementation plans (gitignored)
- Use `docs/superpowers/specs/` for design docs (gitignored)
- Test files: `tests/test_<module>.py`
- No comments unless the WHY is non-obvious

## Git / Security

- `.env` is gitignored — never commit it
- `文档测试/` is gitignored — contains company PDFs
- `docs/` is gitignored — internal design docs
- `__pycache__/`, `*.pyc`, output directories are all gitignored
