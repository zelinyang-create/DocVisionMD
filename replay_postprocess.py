#!/usr/bin/env python3
"""
Replay postprocessing on existing debug files (no VLM re-call).

Reads outline.json + pages/page_*.md from a debug directory, runs the full
postprocess pipeline, and writes the result to postprocess/vN.md inside
that same debug directory (auto-increments N).

Usage:
  python replay_postprocess.py <debug_dir>

Example:
  python replay_postprocess.py \
    "文档测试/NPD2426工艺文件(1)/_debug/NPD2426工艺文件(1)"
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pdf_vlm_md.models import DocumentContext, PageStructure, Heading
from pdf_vlm_md.postprocess import postprocess_markdown


def _next_version(postprocess_dir: Path) -> int:
    nums = []
    for f in postprocess_dir.glob("v*.md"):
        m = re.match(r"v(\d+)\.md$", f.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def load_ctx(debug_dir: Path) -> DocumentContext:
    data = json.loads((debug_dir / "outline.json").read_text(encoding="utf-8"))
    file_title = debug_dir.name
    total_pages = max(int(k) for k in data.keys())
    ctx = DocumentContext(pdf_path=f"{file_title}.pdf", file_title=file_title, total_pages=total_pages)
    for page_str, pd in data.items():
        pno = int(page_str)
        if pd.get("is_toc_page"):
            ctx.toc_pages.append(pno)
        ps = PageStructure(
            page_no=pno,
            is_toc_page=pd.get("is_toc_page", False),
            is_appendix_page=pd.get("is_appendix_page", False),
            is_table_continuation=pd.get("is_table_continuation", False),
        )
        for h in pd.get("headings", []):
            ps.headings.append(Heading(text=h["text"], level=h["level"], type=h.get("type", "body_heading")))
        for h in pd.get("appendix_headings", []):
            ps.appendix_headings.append(Heading(text=h["text"], level=h["level"], type=h.get("type", "appendix_heading")))
        ctx.page_structures[pno] = ps
    return ctx


def assemble_raw(pages_dir: Path) -> str:
    parts = []
    for md_file in sorted(pages_dir.glob("page_*.md")):
        m = re.search(r"page_(\d+)", md_file.stem)
        if not m:
            continue
        pno = int(m.group(1))
        content = md_file.read_text(encoding="utf-8").rstrip("\n")
        parts.append(f"<!-- page: {pno} -->\n{content}\n")
    return "".join(parts)


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <debug_dir>")
        sys.exit(1)
    debug_dir = Path(sys.argv[1])

    postprocess_dir = debug_dir / "postprocess"
    postprocess_dir.mkdir(exist_ok=True)
    version = _next_version(postprocess_dir)
    output = postprocess_dir / f"v{version}.md"

    ctx = load_ctx(debug_dir)
    raw = assemble_raw(debug_dir / "pages")
    result = postprocess_markdown(raw, ctx.file_title, ctx, debug=True)
    output.write_text(result, encoding="utf-8")
    print(f"✓ {output}  ({result.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
