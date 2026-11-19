#!/usr/bin/env python3
"""
Mobile Formatter CLI
将任意 Markdown / HTML / 纯文本文件转换为适配手机阅读的 HTML 与高清长图 (PNG)。
支持保留原 HTML 中的链接、代码高亮与强调颜色，同时注入手机端阅读排版优化样式。
"""

import argparse
import html
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

THEMES = {
    "minimal": {
        "bg": "#ffffff",
        "text": "#1f2328",
        "heading": "#111111",
        "link": "#0969da",
        "quote_bg": "rgba(128, 128, 128, 0.06)",
        "quote_border": "#6b7280",
        "muted": "#57606a",
    },
    "xhs": {
        "bg": "linear-gradient(180deg, #fff5f5 0%, #ffffff 18%, #fffafa 100%)",
        "text": "#2d1f21",
        "heading": "#be123c",
        "link": "#e11d48",
        "quote_bg": "rgba(251, 113, 133, 0.08)",
        "quote_border": "#fb7185",
        "muted": "#881337",
    },
    "wechat": {
        "bg": "#ffffff",
        "text": "#2c2c2c",
        "heading": "#07c160",
        "link": "#576b95",
        "quote_bg": "#f7f7f7",
        "quote_border": "#07c160",
        "muted": "#666666",
    },
    "zhihu": {
        "bg": "#ffffff",
        "text": "#121212",
        "heading": "#0066ff",
        "link": "#175199",
        "quote_bg": "#f6f8fa",
        "quote_border": "#0066ff",
        "muted": "#646464",
    },
    "dark": {
        "bg": "#141820",
        "text": "#e2e8f0",
        "heading": "#f8fafc",
        "link": "#60a5fa",
        "quote_bg": "rgba(255, 255, 255, 0.06)",
        "quote_border": "#60a5fa",
        "muted": "#94a3b8",
    },
}


def inline_md(text: str) -> str:
    s = html.escape(text)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" />', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s


def table_cells(line: str) -> list[str]:
    line = re.sub(r"^\||(?<!\\)\|$", "", line.strip())
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line)]


def table_alignments(header: str, delimiter: str) -> list[str] | None:
    if "|" not in header:
        return None
    cells = table_cells(delimiter)
    if len(cells) != len(table_cells(header)) or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
        return None
    return [
        "center" if cell.startswith(":") and cell.endswith(":") else "right" if cell.endswith(":") else "left"
        for cell in cells
    ]


def md_to_html(md_text: str) -> str:
    lines = md_text.replace("\r\n", "\n").split("\n")
    out = []
    para_buf = []
    in_list = None
    in_code = False
    code_buf = []
    table_end = 0

    def flush_para():
        if not para_buf:
            return
        raw = " ".join(para_buf).strip()
        if raw:
            is_meta = bool(re.match(r"^(发布于|作者：|Posted on|\[本文)", raw)) or bool(
                re.match(r"^\*\[.*\]\*$", raw)
            )
            cls = ' class="meta-line"' if is_meta else ""
            out.append(f"<p{cls}>{inline_md(raw)}</p>")
        para_buf.clear()

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    for i, line in enumerate(lines):
        if i < table_end:
            continue
        if line.strip().startswith("```"):
            if in_code:
                out.append(f"<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>")
                code_buf.clear()
                in_code = False
            else:
                flush_para()
                close_list()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        t = line.strip()
        if not t:
            flush_para()
            close_list()
            continue
        alignments = table_alignments(t, lines[i + 1] if i + 1 < len(lines) else "")
        if alignments:
            flush_para()
            close_list()

            def row(cells, tag):
                cells = (cells + [""] * len(alignments))[:len(alignments)]
                cells = [inline_md(cell.replace(r"\|", "|")) for cell in cells]
                return "<tr>" + "".join(
                    f'<{tag} style="text-align:{align}">{cell}</{tag}>'
                    for cell, align in zip(cells, alignments)
                ) + "</tr>"

            out.append("<table><thead>" + row(table_cells(t), "th") + "</thead><tbody>")
            table_end = i + 2
            while table_end < len(lines) and lines[table_end].strip() and "|" in lines[table_end]:
                out.append(row(table_cells(lines[table_end]), "td"))
                table_end += 1
            out.append("</tbody></table>")
            continue
        if re.match(r"^(---+|\*\*\*+)$", t):
            flush_para()
            close_list()
            out.append("<hr />")
            continue
        hm = re.match(r"^(#{1,6})\s+(.+)$", t)
        if hm:
            flush_para()
            close_list()
            lvl = min(len(hm.group(1)), 3)
            out.append(f"<h{lvl}>{inline_md(hm.group(2))}</h{lvl}>")
            continue
        if t.startswith(">"):
            flush_para()
            close_list()
            out.append(f"<blockquote><p>{inline_md(t.lstrip('> ').strip())}</p></blockquote>")
            continue
        ulm = re.match(r"^[-*+]\s+(.+)$", t)
        if ulm:
            flush_para()
            if in_list != "ul":
                close_list()
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{inline_md(ulm.group(1))}</li>")
            continue
        olm = re.match(r"^\d+\.\s+(.+)$", t)
        if olm:
            flush_para()
            if in_list != "ol":
                close_list()
                out.append("<ol>")
                in_list = "ol"
            out.append(f"<li>{inline_md(olm.group(1))}</li>")
            continue
        close_list()
        para_buf.append(t)

    flush_para()
    close_list()
    return "\n".join(out)


def build_mobile_css(theme_name: str, font_size: int, line_height: float, para_gap: int, padding_x: int, indent: bool) -> str:
    t = THEMES[theme_name]
    indent_val = "2em" if indent else "0"
    return f"""
html, body {{
  margin: 0 !important;
  padding: 0 !important;
  background: {t['bg']} !important;
  color: {t['text']} !important;
  font-family: "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", -apple-system, BlinkMacSystemFont, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}}
#markdown-page, .mobile-article-wrap {{
  max-width: 100% !important;
  width: 100% !important;
  padding: 28px {padding_x}px 38px {padding_x}px !important;
  box-sizing: border-box !important;
}}
#markdown-content, .markdown-viewer-content, .mobile-article-wrap {{
  font-size: {font_size}px !important;
  line-height: {line_height} !important;
  color: {t['text']} !important;
  word-break: break-word;
}}
h1 {{
  font-size: {round(font_size * 1.35)}px !important;
  line-height: 1.35 !important;
  font-weight: 700 !important;
  color: {t['heading']} !important;
  margin: 0 0 12px 0 !important;
  text-align: left !important;
}}
h2 {{
  font-size: {round(font_size * 1.18)}px !important;
  line-height: 1.4 !important;
  font-weight: 700 !important;
  color: {t['heading']} !important;
  margin: 22px 0 10px 0 !important;
}}
h3 {{
  font-size: {round(font_size * 1.06)}px !important;
  line-height: 1.45 !important;
  font-weight: 600 !important;
  color: {t['heading']} !important;
  margin: 18px 0 8px 0 !important;
}}
p {{
  font-size: {font_size}px !important;
  line-height: {line_height} !important;
  text-indent: {indent_val} !important;
  margin: 0 0 {para_gap}px 0 !important;
  text-align: justify !important;
}}
.meta-line,
.md-block[data-block-id="block-2"] p,
.md-block[data-block-id="block-3"] p {{
  text-indent: 0 !important;
  font-size: {max(13, font_size - 4)}px !important;
  line-height: 1.6 !important;
  color: {t['muted']} !important;
  margin: 0 0 8px 0 !important;
}}
.md-block[data-block-id="block-3"] {{
  padding-bottom: 12px !important;
  margin-bottom: 16px !important;
  border-bottom: 1px solid rgba(128, 128, 128, 0.22) !important;
}}
blockquote {{
  margin: 14px 0 !important;
  padding: 10px 14px !important;
  border-left: 4px solid {t['quote_border']} !important;
  background: {t['quote_bg']} !important;
  border-radius: 0 8px 8px 0;
}}
blockquote p {{
  text-indent: 0 !important;
  margin-bottom: 6px !important;
}}
blockquote p:last-child {{ margin-bottom: 0 !important; }}
a {{
  color: {t['link']} !important;
  text-decoration: none !important;
  border-bottom: 1px solid rgba(9, 105, 218, 0.35);
}}
img {{ max-width: 100% !important; height: auto !important; border-radius: 8px; }}
hr {{ border: none; border-top: 1px solid rgba(128,128,128,0.22); margin: 18px 0; }}
table {{
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  margin: 14px 0;
  font-size: 0.78em;
  line-height: 1.6;
}}
th, td {{
  border: 1px solid rgba(128, 128, 128, 0.35);
  padding: 7px;
  vertical-align: top;
  text-align: left;
  overflow-wrap: anywhere;
  text-indent: 0;
}}
th {{ background: rgba(128, 128, 128, 0.1); font-weight: 600; }}
pre {{
  background: #1e293b;
  color: #f8fafc;
  padding: 12px 14px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: {max(12, font_size - 4)}px !important;
  line-height: 1.55 !important;
}}
"""


def inject_css_into_html(raw_html: str, css: str) -> str:
    style_block = f"<style id='mobile-formatter-override'>\n{css}\n</style>"
    if "</head>" in raw_html:
        return raw_html.replace("</head>", f"{style_block}\n</head>", 1)
    return f"<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>{style_block}</head><body>{raw_html}</body></html>"


def wrap_fragment(body_html: str, title: str, css: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)}</title>
  <style>{css}</style>
</head>
<body>
  <div class="mobile-article-wrap">
    {body_html}
  </div>
</body>
</html>"""


def render_png_with_agent_browser(html_path: Path, png_path: Path, width: int, scale: int) -> None:
    session = f"mobile-fmt-{os.getpid()}"
    cmds = [
        ["agent-browser", "--session", session, "set", "viewport", str(width), "900", str(scale)],
        ["agent-browser", "--session", session, "open", html_path.resolve().as_uri()],
        ["agent-browser", "--session", session, "wait", "--load", "networkidle"],
        ["agent-browser", "--session", session, "screenshot", "--full", str(png_path.resolve())],
    ]
    try:
        for cmd in cmds:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        subprocess.run(
            ["agent-browser", "--session", session, "close"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def main():
    parser = argparse.ArgumentParser(description="本地通用手机适配排版工具 (支持 .md / .html / .txt)")
    parser.add_argument("input", help="输入文件路径 (.md / .html / .txt)")
    parser.add_argument("-o", "--output", help="输出路径 (.png 或 .html)，默认同目录生成 -mobile.png")
    parser.add_argument("--theme", choices=list(THEMES.keys()), default="minimal", help="排版主题 (默认: minimal)")
    parser.add_argument("--width", type=int, default=430, help="手机视口宽度 px (默认: 430)")
    parser.add_argument("--font-size", type=int, default=18, help="正文字号 px (默认: 18)")
    parser.add_argument("--line-height", type=float, default=1.82, help="行高 (默认: 1.82)")
    parser.add_argument("--para-gap", type=int, default=14, help="段落间距 px (默认: 14)")
    parser.add_argument("--padding-x", type=int, default=20, help="左右边距 px (默认: 20)")
    parser.add_argument("--no-indent", action="store_true", help="关闭中文首行缩进")
    parser.add_argument("--scale", type=int, default=2, choices=[1, 2, 3], help="图片导出倍率 (默认: 2)")
    args = parser.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    if not in_path.exists():
        print(f"错误：找不到输入文件 {in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else in_path.with_name(f"{in_path.stem}-mobile.png")
    )

    raw = in_path.read_text(encoding="utf-8")
    css = build_mobile_css(
        args.theme, args.font_size, args.line_height, args.para_gap, args.padding_x, not args.no_indent
    )

    ext = in_path.suffix.lower()
    if ext in {".html", ".htm"}:
        # 保留原 HTML 中的高亮颜色、链接与结构，仅覆盖手机阅读排版样式
        final_html = inject_css_into_html(raw, css)
    elif ext in {".md", ".markdown"}:
        body = md_to_html(raw)
        final_html = wrap_fragment(body, in_path.stem, css)
    else:
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        body = "\n".join(
            f"<h1>{html.escape(l)}</h1>" if (i == 0 and len(l) < 45) else f"<p>{html.escape(l)}</p>"
            for i, l in enumerate(lines)
        )
        final_html = wrap_fragment(body, in_path.stem, css)

    if out_path.suffix.lower() in {".html", ".htm"}:
        out_path.write_text(final_html, encoding="utf-8")
        print(f"已生成手机版 HTML: {out_path}")
        return

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(final_html)
        tmp_html_path = Path(tmp.name)

    try:
        render_png_with_agent_browser(tmp_html_path, out_path, args.width, args.scale)
        print(f"已生成手机适配高清长图: {out_path}")
    finally:
        tmp_html_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
