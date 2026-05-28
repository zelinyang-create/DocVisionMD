from pathlib import Path
from unittest.mock import patch, MagicMock

import fitz

from pdf_vlm_md.models import DocumentContext, PageStructure
from pdf_vlm_md.outline import run_phase1


def test_vlm_failure_falls_back_to_pymupdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    body = "1 项目概述\n\n" + "这是正文内容，用于满足文本层最小字符数要求。" * 3
    page.insert_text((72, 72), body)
    doc.save(str(pdf_path))
    doc.close()

    img_path = tmp_path / "page_001.png"
    img_path.write_bytes(b"fake")

    ctx = DocumentContext(
        pdf_path=str(pdf_path),
        file_title="test",
        total_pages=1,
    )

    with patch("pdf_vlm_md.outline.extract_page_structure_vlm", side_effect=RuntimeError("VLM down")):
        with patch("pdf_vlm_md.outline.choose_extraction_method", return_value="vlm"):
            result, _ = run_phase1(str(pdf_path), [img_path], ctx)

    ps = result.page_structures[1]
    assert ps.extraction_method == "hybrid"
    assert ps.headings or ps.structure_confidence > 0
