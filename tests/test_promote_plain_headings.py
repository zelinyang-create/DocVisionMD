from pdf_vlm_md.postprocess import (
    demote_list_items_in_flowchart_sections,
    fix_flowchart_page_titles,
)


def test_demote_numbered_list_inside_flowchart_summary():
    inp = """#### 流程链路总结
本页内容非线性流程：
## 1. **输入条件**：确定焊接方式。
## 2. **查表路径 A**：查阅载流焊表。
"""
    out = demote_list_items_in_flowchart_sections(inp)
    assert '## 1.' not in out
    assert '1. **输入条件**：确定焊接方式。' in out
    assert '2. **查表路径 A**：查阅载流焊表。' in out


def test_fix_flowchart_page_title_from_meta_heading():
    inp = """### 工艺流程图

**火炬电子 CTK41B型多层片式瓷介固定电容器工艺规程**
**流程图**

执行标准：GJB 1928-2011
"""
    out = fix_flowchart_page_titles(inp)
    assert '### 工艺流程图' not in out
    assert '### 火炬电子 CTK41B型多层片式瓷介固定电容器工艺规程 流程图' in out
    assert '**流程图**' not in out
