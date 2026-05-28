from pdf_vlm_md.postprocess import fix_numbered_heading_levels


def test_fixes_1_1_from_h2_to_h3():
    inp = "## 1.1 建设背景"
    out = fix_numbered_heading_levels(inp)
    assert out.strip() == "### 1.1 建设背景"


def test_fixes_1_1_1_from_h2_to_h4():
    inp = "## 1.1.1 数据来源"
    out = fix_numbered_heading_levels(inp)
    assert out.strip() == "#### 1.1.1 数据来源"


def test_preserves_correct_h2():
    inp = "## 1 项目概述"
    out = fix_numbered_heading_levels(inp)
    assert out.strip() == "## 1 项目概述"


def test_skips_code_blocks():
    inp = "```\n## 1.1 not a heading\n```"
    out = fix_numbered_heading_levels(inp)
    assert out == inp
