#!/usr/bin/env python3
"""
Generate an HTML side-by-side comparison of Phase 1.5 vs postprocessed heading trees.

Sources:
  <debug_dir>/outline.json              — Phase 1.5 (post-relevel extracted structure)
  <debug_dir>/postprocess/vN.md         — latest postprocessed output (auto-detected)

Output:
  <debug_dir>/compare/vN_compare.html   — auto-increments N

Usage:
  python gen_heading_comparison.py <debug_dir>
"""
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path


@dataclass
class HEntry:
    page: int
    text: str
    level: int
    tag: str  # 'body' | 'appendix'


# ── helpers ──────────────────────────────────────────────────────────────────

def _next_compare_version(compare_dir: Path) -> int:
    nums = []
    for f in compare_dir.glob("v*_compare.html"):
        m = re.match(r"v(\d+)_compare\.html$", f.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def _latest_postprocess(postprocess_dir: Path) -> Path | None:
    candidates = []
    for f in postprocess_dir.glob("v*.md"):
        m = re.match(r"v(\d+)\.md$", f.name)
        if m:
            candidates.append((int(m.group(1)), f))
    return max(candidates, key=lambda x: x[0])[1] if candidates else None


# ── data loading ──────────────────────────────────────────────────────────────

def load_p15(debug_dir: Path) -> tuple[list[HEntry], set[int]]:
    data = json.loads((debug_dir / 'outline.json').read_text(encoding='utf-8'))
    entries: list[HEntry] = []
    toc_pages: set[int] = set()
    for page_str, pd in sorted(data.items(), key=lambda x: int(x[0])):
        pno = int(page_str)
        if pd.get('is_toc_page'):
            toc_pages.add(pno)
        for h in pd.get('headings', []):
            entries.append(HEntry(pno, h['text'], h['level'], 'body'))
        for h in pd.get('appendix_headings', []):
            entries.append(HEntry(pno, h['text'], h['level'], 'appendix'))
    return entries, toc_pages


def load_final_output(md_path: Path) -> list[HEntry]:
    entries: list[HEntry] = []
    current_page = 0
    for line in md_path.read_text(encoding='utf-8').splitlines():
        pm = re.match(r'^<!-- page: (\d+) -->', line)
        if pm:
            current_page = int(pm.group(1))
            continue
        if current_page == 0:
            continue
        hm = re.match(r'^(#{1,6})\s+(.+)', line)
        if hm:
            entries.append(HEntry(current_page, hm.group(2).strip(), len(hm.group(1)), 'body'))
    return entries


# ── matching ──────────────────────────────────────────────────────────────────

def _key(text: str) -> str:
    return re.sub(r'\s+', '', text).lower()


Pair = tuple[HEntry | None, HEntry | None, str]


def match_page(p15: list[HEntry], p2: list[HEntry]) -> list[Pair]:
    used = [False] * len(p2)
    pairs: list[Pair] = []

    for e15 in p15:
        k = _key(e15.text)
        best_i, best_score = -1, 0
        for i, e2 in enumerate(p2):
            if used[i]:
                continue
            k2 = _key(e2.text)
            if k == k2:
                best_i, best_score = i, 2
                break
            if k and k2 and (k in k2 or k2 in k):
                score = min(len(k), len(k2)) / max(len(k), len(k2))
                if score > best_score:
                    best_i, best_score = i, score

        if best_i >= 0 and best_score >= 0.6:
            e2 = p2[best_i]
            used[best_i] = True
            status = 'match' if e15.level == e2.level else 'level_diff'
            pairs.append((e15, e2, status))
        else:
            pairs.append((e15, None, 'only_p15'))

    for i, e2 in enumerate(p2):
        if not used[i]:
            pairs.append((None, e2, 'only_p2'))

    return pairs


# ── HTML rendering ────────────────────────────────────────────────────────────

def _entry_html(entry: HEntry | None, status: str) -> str:
    if entry is None:
        return ''
    indent_px = (entry.level - 2) * 16
    badge_text = f'H{entry.level}'
    css = 'he'
    if status == 'level_diff':
        css += ' ld'
    elif status in ('only_p15', 'only_p2'):
        css += ' ox'
    if entry.tag == 'appendix':
        css += ' ap'
    return (
        f'<div class="{css}" style="padding-left:{indent_px}px">'
        f'<span class="hb">{badge_text}</span>'
        f'<span class="ht">{escape(entry.text)}</span>'
        f'</div>'
    )


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;font-size:13px;background:#f0f2f5;color:#222}
a{color:inherit;text-decoration:none}
.topbar{background:#16213e;color:#fff;padding:14px 24px;display:flex;align-items:baseline;gap:16px}
.topbar h1{font-size:16px;font-weight:700}
.topbar p{font-size:11px;opacity:.6}
.stats{display:flex;flex-wrap:wrap;gap:10px;padding:12px 20px;background:#fff;border-bottom:1px solid #dde}
.stat{background:#f8f9fb;border:1px solid #e4e6ea;border-radius:8px;padding:8px 14px;min-width:100px}
.sl{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:#888}
.sv{font-size:22px;font-weight:800;line-height:1.1;margin-top:2px}
.sv.g{color:#16a34a}.sv.y{color:#ca8a04}.sv.r{color:#dc2626}.sv.b{color:#2563eb}
.legend{display:flex;gap:18px;padding:7px 20px;background:#fff;border-bottom:1px solid #dde;font-size:11px;flex-wrap:wrap}
.li{display:flex;align-items:center;gap:5px}
.ld-dot{width:10px;height:10px;border-radius:3px;flex-shrink:0}
.jumpbar{padding:6px 20px;background:#f8f9fb;border-bottom:1px solid #dde;font-size:11px;color:#666;white-space:nowrap;overflow-x:auto}
.jumpbar a{display:inline-block;margin:2px 4px 2px 0;padding:2px 7px;background:#fef3c7;border:1px solid #fcd34d;border-radius:4px;color:#92400e;font-weight:600;white-space:nowrap}
.colh{display:grid;grid-template-columns:56px 1fr 1fr;background:#1e3a5f;color:#fff;position:sticky;top:0;z-index:10}
.colh>div{padding:8px 14px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;border-right:1px solid rgba(255,255,255,.12)}
.pr{display:grid;grid-template-columns:56px 1fr 1fr;border-bottom:1px solid #e8eaed}
.pr:hover{background:#f7f9ff}
.pr.diff{background:#fffdf0}
.pr.diff:hover{background:#fffaee}
.pn{text-align:center;padding:8px 4px 4px;font-size:11px;color:#aaa;font-weight:700;border-right:1px solid #e8eaed;display:flex;flex-direction:column;align-items:center}
.pn .tl{font-size:9px;color:#bbb;font-style:italic;margin-top:2px}
.cell{padding:5px 10px;border-right:1px solid #e8eaed;min-height:30px}
.empty{color:#ccc;font-size:11px;padding:7px 2px;font-style:italic}
.he{display:flex;align-items:baseline;gap:5px;padding:2px 4px;border-radius:3px;margin:1px 0}
.hb{font-size:10px;font-weight:800;background:#eef;color:#555;border-radius:3px;padding:1px 4px;flex-shrink:0;letter-spacing:.3px}
.ht{font-size:12px;line-height:1.5}
.he.ld{background:#fffbe6}
.he.ld .hb{background:#fef9c3;color:#92400e}
.he.ld .ht{color:#92400e}
.he.ox{background:#fff0f0}
.he.ox .hb{background:#fee2e2;color:#991b1b}
.he.ox .ht{color:#b91c1c}
.he.ap .hb{background:#dbeafe;color:#1d4ed8}
.pn.hasdiff .pno{color:#ca8a04;font-weight:900}
"""

HTML = """\
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>{title} — 标题层次对比</title>
<style>{css}</style>
</head>
<body>
<div class="topbar">
  <h1>{title}</h1>
  <p>Phase 1.5（outline.json）vs 后处理输出（{postprocess_file}）</p>
</div>
<div class="stats">
  <div class="stat"><div class="sl">总页数</div><div class="sv b">{total_pages}</div></div>
  <div class="stat"><div class="sl">有标题页</div><div class="sv b">{pages_with_headings}</div></div>
  <div class="stat"><div class="sl">P1.5 标题</div><div class="sv b">{p15_count}</div></div>
  <div class="stat"><div class="sl">后处理标题</div><div class="sv b">{p2_count}</div></div>
  <div class="stat"><div class="sl">层级不符</div><div class="sv y">{cnt_ld}</div></div>
  <div class="stat"><div class="sl">仅 P1.5 有</div><div class="sv r">{cnt_p15}</div></div>
  <div class="stat"><div class="sl">仅后处理有</div><div class="sv r">{cnt_p2}</div></div>
  <div class="stat"><div class="sl">完全匹配页</div><div class="sv g">{perfect_pages}</div></div>
</div>
<div class="legend">
  <span class="li"><span class="ld-dot" style="background:#eef;border:1px solid #c7d2fe"></span>两侧一致</span>
  <span class="li"><span class="ld-dot" style="background:#fffbe6;border:1px solid #fcd34d"></span>层级不同</span>
  <span class="li"><span class="ld-dot" style="background:#fff0f0;border:1px solid #fca5a5"></span>仅一侧有</span>
  <span class="li"><span class="ld-dot" style="background:#dbeafe;border:1px solid #93c5fd"></span>附录标题 (P1.5)</span>
</div>
{jumpbar}
<div class="colh">
  <div>页</div>
  <div>Phase 1.5 — outline.json（结构提取 + LLM 重排）</div>
  <div>后处理输出 — {postprocess_file}</div>
</div>
{rows}
</body>
</html>
"""


def generate(debug_dir: Path) -> None:
    postprocess_dir = debug_dir / "postprocess"
    compare_dir = debug_dir / "compare"
    compare_dir.mkdir(exist_ok=True)

    final_md = _latest_postprocess(postprocess_dir)
    if final_md is None:
        print(f"错误：{postprocess_dir} 中未找到 v*.md 文件，请先运行 replay_postprocess.py")
        sys.exit(1)

    version = _next_compare_version(compare_dir)
    output = compare_dir / f"v{version}_compare.html"

    p15_entries, toc_pages = load_p15(debug_dir)
    p2_entries = load_final_output(final_md)

    p15_map: dict[int, list[HEntry]] = defaultdict(list)
    for e in p15_entries:
        p15_map[e.page].append(e)

    p2_map: dict[int, list[HEntry]] = defaultdict(list)
    for e in p2_entries:
        p2_map[e.page].append(e)

    all_pages = sorted(set(p15_map) | set(p2_map))

    rows_html: list[str] = []
    diff_pages: list[int] = []
    cnt_ld = cnt_p15 = cnt_p2 = perfect_pages = 0
    pages_with_headings = 0

    for pno in all_pages:
        e15s = p15_map.get(pno, [])
        e2s = p2_map.get(pno, [])
        if not e15s and not e2s:
            continue
        pages_with_headings += 1

        pairs = match_page(e15s, e2s)
        has_diff = False
        left_cells = right_cells = ''

        for e15, e2, status in pairs:
            if status == 'level_diff':
                cnt_ld += 1
                has_diff = True
            elif status == 'only_p15':
                cnt_p15 += 1
                has_diff = True
            elif status == 'only_p2':
                cnt_p2 += 1
                has_diff = True

            left_cells += _entry_html(e15, status)
            right_cells += _entry_html(e2, status)

        if not has_diff:
            perfect_pages += 1
        else:
            diff_pages.append(pno)

        is_toc = pno in toc_pages
        row_cls = 'pr' + (' diff' if has_diff else '')
        pn_cls = 'pn' + (' hasdiff' if has_diff else '')
        toc_mark = '<span class="tl">TOC</span>' if is_toc else ''

        empty = '<span class="empty">(无)</span>'
        rows_html.append(
            f'<div class="{row_cls}" id="p{pno}">'
            f'<div class="{pn_cls}"><span class="pno">{pno}</span>{toc_mark}</div>'
            f'<div class="cell">{left_cells or empty}</div>'
            f'<div class="cell">{right_cells or empty}</div>'
            f'</div>'
        )

    jump_links = ''
    if diff_pages:
        jump_links = '差异页快跳：' + ''.join(
            f'<a href="#p{p}">{p}</a>' for p in diff_pages
        )
    jumpbar = f'<div class="jumpbar">{jump_links}</div>' if jump_links else ''

    html = HTML.format(
        title=debug_dir.name,
        css=CSS,
        postprocess_file=final_md.name,
        total_pages=max(all_pages) if all_pages else 0,
        pages_with_headings=pages_with_headings,
        p15_count=len(p15_entries),
        p2_count=len(p2_entries),
        cnt_ld=cnt_ld,
        cnt_p15=cnt_p15,
        cnt_p2=cnt_p2,
        perfect_pages=perfect_pages,
        jumpbar=jumpbar,
        rows='\n'.join(rows_html),
    )

    output.write_text(html, encoding='utf-8')
    print(f'✓ {output}  ({pages_with_headings} pages, {cnt_ld} level diffs, '
          f'{cnt_p15} only-P15, {cnt_p2} only-postprocess)')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} <debug_dir>')
        sys.exit(1)
    generate(Path(sys.argv[1]))
