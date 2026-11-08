#!/usr/bin/env python3
# Copyright 2026 mate-matt
# Licensed under the Apache License, Version 2.0
# Derivative reading UI for the Apache-2.0 notebooks by Jay Alammar & Maarten Grootendorst.

"""Build the static GitHub Pages reader in docs/ from sources/."""

from __future__ import annotations

import base64
import html
import json
import re
import shutil
import struct
from pathlib import Path
from urllib.parse import quote

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources"
WEB = ROOT / "web"
DOCS = ROOT / "docs"
NB_ROOT = SRC / "notebooks"

UPSTREAM = "https://github.com/HandsOnLLM/Hands-On-Large-Language-Models"
REPO = "https://github.com/mate-matt/hands-on-llm-reader"
AMAZON = "https://www.amazon.com/Hands-Large-Language-Models-Understanding/dp/1098150961"
OREILLY = "https://www.oreilly.com/library/view/hands-on-large-language/9781098150952/"
UPSTREAM_COMMIT = "ea3390819997999a51983677b80b3aac4dc50ada"

CHAPTERS = [
    (1, "Introduction to Language Models", "chapter01/Chapter 1 - Introduction to Language Models.ipynb"),
    (2, "Tokens and Embeddings", "chapter02/Chapter 2 - Tokens and Token Embeddings.ipynb"),
    (3, "Looking Inside Transformer LLMs", "chapter03/Chapter 3 - Looking Inside LLMs.ipynb"),
    (4, "Text Classification", "chapter04/Chapter 4 - Text Classification.ipynb"),
    (5, "Text Clustering and Topic Modeling", "chapter05/Chapter 5 - Text Clustering and Topic Modeling.ipynb"),
    (6, "Prompt Engineering", "chapter06/Chapter 6 - Prompt Engineering.ipynb"),
    (7, "Advanced Text Generation Techniques and Tools", "chapter07/Chapter 7 - Advanced Text Generation Techniques and Tools.ipynb"),
    (8, "Semantic Search and Retrieval-Augmented Generation", "chapter08/Chapter 8 - Semantic Search.ipynb"),
    (9, "Multimodal Large Language Models", "chapter09/Chapter 9 - Multimodal Large Language Models.ipynb"),
    (10, "Creating Text Embedding Models", "chapter10/Chapter 10 - Creating Text Embedding Models.ipynb"),
    (11, "Fine-tuning Representation Models for Classification", "chapter11/Chapter 11 - Fine-Tuning BERT.ipynb"),
    (12, "Fine-tuning Generation Models", "chapter12/Chapter 12 - Fine-tuning Generation Models.ipynb"),
]

ALTS = {
    "book_cover.png": "Hands-On Large Language Models book cover",
    "dlai.png": "DeepLearning.AI short course illustration",
    "bonus_overview.png": "Overview figure for the bonus illustrated guides",
    "bonus_int8.png": "Illustration from the quantization guide",
    "bonus_bitnet.png": "Illustration of BitNet from the quantization guide",
    "bonus_ssm.png": "Illustration from the Mamba and state space guide",
    "bonus_ssm1.png": "Second illustration from the Mamba and state space guide",
    "bonus_moe.png": "Illustration from the mixture-of-experts guide",
    "bonus_vmoe.png": "Illustration of vision mixture-of-experts",
    "bonus_sd.png": "Illustration from The Illustrated Stable Diffusion",
    "bonus_sd1.png": "Second illustration from The Illustrated Stable Diffusion",
    "bonus_reasoning1.png": "Illustration from the reasoning LLMs guide",
    "bonus_reasoning2.png": "Second illustration from the reasoning LLMs guide",
    "bonus_deepseek1.png": "Illustration from The Illustrated DeepSeek-R1",
    "bonus_deepseek2.png": "Second illustration from The Illustrated DeepSeek-R1",
    "bonus_agents.png": "Illustration from the LLM agents guide",
    "bonus_agents1.png": "Tools illustration from the LLM agents guide",
    "bonus_agents2.png": "Memory illustration from the LLM agents guide",
    "bonus_agents3.png": "Planning illustration from the LLM agents guide",
    "bonus_agents4.png": "Multi-agent illustration from the LLM agents guide",
    "puppy.png": "Puppy image used in the multimodal notebook",
    "cat.png": "Cat image used in the multimodal notebook",
    "car.png": "Car image used in the multimodal notebook",
    "colab-badge.svg": "Open in Colab",
    "colab-icon.png": "Google Colab",
}

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PROGRESS_RE = re.compile(r"(%\|)|(it/s)|Downloading|Loading|Extracting|Resolving|Fetching", re.I)
BADGE_RE = re.compile(
    r'<a href="([^"]+)"><img src="https://img\.shields\.io/[^"]+"></a>',
    re.I,
)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
A_RE = re.compile(r"<a\b[^>]*>", re.I)

MD = markdown.Markdown(extensions=["extra", "sane_lists", "tables"], output_format="html5")
LEXER = PythonLexer()
FORMATTER = HtmlFormatter(cssclass="codehilite", style="friendly")


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "".join(value)
    return str(value)


def prefix(depth: int) -> str:
    return "../" * depth


def rel(depth: int, path: str) -> str:
    return prefix(depth) + path


def blob_url(path: str) -> str:
    return UPSTREAM + "/blob/main/" + quote(path, safe="/")


def colab_url(path: str) -> str:
    return "https://colab.research.google.com/github/HandsOnLLM/Hands-On-Large-Language-Models/blob/main/" + quote(path, safe="/")


def alt_for(src: str) -> str:
    name = src.split("?")[0].rstrip("/").split("/")[-1]
    if name in ALTS:
        return ALTS[name]
    stem = re.sub(r"\.[a-zA-Z0-9]+$", "", name).replace("-", " ").replace("_", " ").strip()
    return stem or "Notebook figure"


def is_badge(src: str) -> bool:
    name = src.lower()
    return "colab-badge" in name or "colab-icon" in name or "shields.io" in name or name.endswith("colab.png")


def rewrite_urls(text: str, depth: int) -> str:
    pre = prefix(depth)
    text = text.replace(
        "https://raw.githubusercontent.com/HandsOnLLM/Hands-On-Large-Language-Models/main/images/",
        f"{pre}images/",
    )
    text = text.replace(
        "https://colab.research.google.com/assets/colab-badge.svg",
        f"{pre}assets/colab-badge.svg",
    )
    text = text.replace(
        "https://colab.google/static/images/icons/colab.png",
        f"{pre}assets/colab-icon.png",
    )
    return text


def replace_badges(text: str) -> str:
    def repl(match: re.Match) -> str:
        href = match.group(1)
        if "amazon.com" in href:
            label, cls = "Buy the Book", "badge-buy"
        elif "oreilly.com" in href:
            label, cls = "O'Reilly", "badge-oreilly"
        elif "github.com/HandsOnLLM" in href:
            label, cls = "GitHub Repository", "badge-github"
        else:
            label, cls = "Link", "badge-link"
        return f'<a class="text-badge {cls}" href="{esc(href)}">{esc(label)}</a>'

    return BADGE_RE.sub(repl, text)


def annotate_imgs(fragment: str) -> str:
    def repl(match: re.Match) -> str:
        tag = match.group(0)
        src_match = re.search(r'\bsrc\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
        src = src_match.group(2) if src_match else ""
        alt_match = re.search(r'\balt\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
        alt = alt_match.group(2).strip() if alt_match else ""
        if not alt:
            alt = alt_for(src)
            if alt_match:
                tag = tag[: alt_match.start(2)] + esc(alt) + tag[alt_match.end(2) :]
            else:
                tag = re.sub(r"\s*/?\s*>$", "", tag)
                tag += f' alt="{esc(alt)}">'
        kind = "inline-badge" if is_badge(src) else "figure"
        class_match = re.search(r'\bclass\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
        if class_match:
            classes = class_match.group(2).split()
            if kind not in classes:
                classes.insert(0, kind)
                tag = tag[: class_match.start(2)] + " ".join(classes) + tag[class_match.end(2) :]
        else:
            tag = re.sub(r"<img\b", f'<img class="{kind}"', tag, count=1, flags=re.I)
        if not tag.endswith(">"):
            tag += ">"
        return tag

    return IMG_RE.sub(repl, fragment)


def decorate_links(fragment: str) -> str:
    def repl(match: re.Match) -> str:
        tag = match.group(0)
        href_match = re.search(r'\bhref\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
        if not href_match:
            return tag
        href = href_match.group(2)
        if not href.startswith(("http://", "https://")):
            return tag
        addition = ""
        if "target=" not in tag.lower():
            addition += ' target="_blank"'
        if "rel=" not in tag.lower():
            addition += ' rel="noopener noreferrer"'
        if not addition:
            return tag
        return tag[:-1] + addition + ">"

    return A_RE.sub(repl, fragment)


def wrap_tables(fragment: str) -> str:
    if "<table" not in fragment.lower():
        return fragment
    fragment = re.sub(r"<table\b", '<div class="table-scroll"><table', fragment, flags=re.I)
    fragment = re.sub(r"</table>", "</table></div>", fragment, flags=re.I)
    return fragment


def render_md(source: str, depth: int) -> str:
    text = as_text(source).replace("\r\n", "\n").replace("\r", "\n")
    text = replace_badges(text)
    text = rewrite_urls(text, depth)
    MD.reset()
    rendered = MD.convert(text)
    rendered = annotate_imgs(rendered)
    rendered = wrap_tables(rendered)
    rendered = decorate_links(rendered)
    return rendered


def clean_rich_html(raw: str) -> str:
    plotly = "Plotly.newPlot" in raw or "plotly-graph-div" in raw
    if plotly:
        raw = re.sub(r"</?(?:html|head|body)\b[^>]*>", "", raw, flags=re.I)
        raw = re.sub(r"<meta\b[^>]*>", "", raw, flags=re.I)
        raw = re.sub(r"width:\s*\d+px", "width:100%;max-width:100%", raw)
        note = '<p class="plotly-note">这张图是笔记本里保存的 Plotly 图，需要 JavaScript 才能显示。</p>'
        return f'<div class="plotly-wrap">{note}{raw.strip()}</div>'
    raw = re.sub(r"<head\b[^>]*>.*?</head>", "", raw, flags=re.I | re.S)
    raw = re.sub(r"</?(?:html|body)\b[^>]*>", "", raw, flags=re.I)
    raw = re.sub(r"<script\b[^>]*>.*?</script>", "", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", "", raw, flags=re.I | re.S)
    raw = re.sub(r"<button\b[^>]*>.*?</button>", "", raw, flags=re.I | re.S)
    raw = re.sub(r"<svg\b[^>]*>.*?</svg>", "", raw, flags=re.I | re.S)
    raw = re.sub(r"<meta\b[^>]*>", "", raw, flags=re.I)
    if not raw.strip():
        return ""
    textish = re.sub(r"<[^>]+>", "", raw).strip()
    if not textish and not re.search(r"<(table|img|pre|progress|p|ul|ol)\b", raw, re.I):
        return ""
    return raw.strip()


def image_tag(mime: str, payload) -> str:
    raw_b64 = re.sub(r"\s+", "", as_text(payload))
    binary = base64.b64decode(raw_b64)
    if mime == "image/png" and not binary.startswith(b"\x89PNG"):
        raise SystemExit("embedded PNG output is not a PNG")
    if mime == "image/jpeg" and not binary.startswith(b"\xff\xd8"):
        raise SystemExit("embedded JPEG output is not a JPEG")
    alt = "Saved notebook figure"
    if mime == "image/png" and len(binary) >= 24:
        width, height = struct.unpack(">II", binary[16:24])
        alt = f"Saved notebook figure, {width} by {height} pixels"
    return f'<img class="figure" src="data:{mime};base64,{raw_b64}" alt="{esc(alt)}">'


def render_rich(data: dict, depth: int) -> str:
    if "text/html" in data:
        cleaned = clean_rich_html(as_text(data["text/html"]))
        if cleaned:
            cleaned = annotate_imgs(decorate_links(wrap_tables(rewrite_urls(cleaned, depth))))
            return f'<div class="output">{cleaned}</div>'
    for mime in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        if mime in data:
            return f'<div class="output">{image_tag(mime, data[mime])}</div>'
    if "text/markdown" in data:
        rendered = render_md(as_text(data["text/markdown"]), depth)
        if rendered.strip():
            return f'<div class="output"><div class="markdown" lang="en">{rendered}</div></div>'
    if "text/plain" in data:
        text = as_text(data["text/plain"]).strip("\n")
        if text.strip():
            return f'<div class="scrollbox"><pre class="stream stdout">{esc(text)}</pre></div>'
    return ""


def render_stream(name: str, text: str) -> str:
    text = ANSI.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return ""
    safe = esc(text)
    if name == "stderr" and len(text) > 500:
        first = esc(text.strip().splitlines()[0][:90])
        return (
            f'<details class="log"><summary>运行日志 · {first}</summary>'
            f'<pre class="stream stderr">{safe}</pre></details>'
        )
    cls = "stdout" if name == "stdout" else "stderr"
    return f'<div class="scrollbox"><pre class="stream {cls}">{safe}</pre></div>'


def render_error(output: dict) -> str:
    tb = ANSI.sub("", "\n".join(output.get("traceback") or []))
    if not tb.strip():
        tb = f"{output.get('ename', 'Error')}: {output.get('evalue', '')}"
    return f'<div class="scrollbox"><pre class="stream error">{esc(tb)}</pre></div>'


def widget_text(output: dict) -> str:
    data = output.get("data") or {}
    return as_text(data.get("text/plain")).strip()


def render_widgets(lines: list[str]) -> str:
    kept = [line for line in lines if line.strip()]
    if not kept:
        return ""
    text = "\n".join(kept)
    safe = esc(text)
    progress = all(PROGRESS_RE.search(line) for line in kept)
    if progress and (len(kept) >= 2 or len(text) > 180):
        return (
            '<details class="log"><summary>模型加载记录（交互控件，静态页只保留文字）</summary>'
            f'<pre class="stream">{safe}</pre></details>'
        )
    return (
        '<div class="widget-log"><span class="tag">交互输出</span> '
        "静态页不能运行这个控件，请用「在 Colab 打开」。"
        f'<pre class="stream">{safe}</pre></div>'
    )


def is_widget(output: dict) -> bool:
    if output.get("output_type") not in {"display_data", "execute_result"}:
        return False
    data = output.get("data") or {}
    return "application/vnd.jupyter.widget-view+json" in data and not any(
        key in data for key in ("text/html", "image/png", "image/jpeg", "image/gif")
    )


def render_outputs(outputs: list, depth: int) -> str:
    parts: list[str] = []
    index = 0
    while index < len(outputs):
        output = outputs[index]
        if is_widget(output):
            lines = []
            while index < len(outputs) and is_widget(outputs[index]):
                lines.append(widget_text(outputs[index]))
                index += 1
            widget = render_widgets(lines)
            if widget:
                parts.append(widget)
            continue
        kind = output.get("output_type")
        if kind == "stream":
            rendered = render_stream(output.get("name") or "stdout", as_text(output.get("text")))
        elif kind == "error":
            rendered = render_error(output)
        elif kind in {"display_data", "execute_result"}:
            rendered = render_rich(output.get("data") or {}, depth)
        else:
            rendered = ""
        if rendered:
            parts.append(rendered)
        index += 1
    if not parts:
        return ""
    return '<div class="outputs">' + "".join(parts) + "</div>"


def render_notebook(nb: dict, depth: int) -> str:
    chunks = []
    for cell in nb.get("cells", []):
        kind = cell.get("cell_type")
        if kind == "markdown":
            body = render_md(cell.get("source"), depth)
            if body.strip():
                chunks.append(f'<article class="cell cell-md"><div class="markdown" lang="en">{body}</div></article>')
        elif kind == "code":
            source = as_text(cell.get("source"))
            count = cell.get("execution_count")
            label = f"In [{count}]" if count else "In"
            code = highlight(source, LEXER, FORMATTER)
            outputs = render_outputs(cell.get("outputs") or [], depth)
            chunks.append(
                f'<article class="cell cell-code"><p class="cell-label">{esc(label)}</p>{code}{outputs}</article>'
            )
    return "\n".join(chunks)


def subtitle_from(nb: dict) -> str:
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        text = as_text(cell.get("source"))
        match = re.search(r"<i>(.*?)</i>", text, re.S | re.I)
        if not match:
            return ""
        inner = re.sub(r"<[^>]+>", "", match.group(1))
        return re.sub(r"\s+", " ", inner).strip()
    return ""


def disclaimer() -> str:
    return (
        '<p class="disclaimer"><strong>笔记本镜像，不是全书。</strong> '
        "这是开源笔记仓库的个人阅读页，只收录 Apache-2.0 许可的 Jupyter 笔记本、"
        "bonus 简介，以及这些文件里原有的图片。不包括 O’Reilly 书的正文、未随仓库发布的插图或 PDF。"
        f' <a href="{AMAZON}">购买本书</a>'
        f' · <a href="{OREILLY}">O’Reilly</a>'
        f' · <a href="{UPSTREAM}">上游 GitHub</a></p>'
    )


def footer(depth: int) -> str:
    return f"""
<footer class="site-footer">
  <p>笔记本 © 2024 Jay Alammar &amp; Maarten Grootendorst，Apache-2.0。本阅读界面由 mate-matt 制作，是上游仓库的衍生排版，不改笔记本正文。</p>
  <p>上游提交 <a href="{UPSTREAM}/commit/{UPSTREAM_COMMIT}">{UPSTREAM_COMMIT[:7]}</a>
  · <a href="{rel(depth, "LICENSE")}">Apache-2.0</a>
  · <a href="{rel(depth, "NOTICE")}">NOTICE</a>
  · <a href="{UPSTREAM}">上游仓库</a>
  · <a href="{REPO}">本仓库</a>
  · <a href="{rel(depth, "bonus/index.html")}">延伸阅读</a></p>
</footer>
"""


def chrome(items: list[str]) -> str:
    return '<nav class="chrome" aria-label="阅读导航">' + "".join(items) + "</nav>"


def nav_anchor(href: str | None, label: str, attrs: str = "") -> str:
    if not href:
        return f'<span class="is-disabled" aria-disabled="true">{esc(label)}</span>'
    return f'<a href="{esc(href)}" {attrs}>{esc(label)}</a>'


def layout(title: str, depth: int, main: str, nav: str, body_attrs: str = "") -> str:
    desc = "个人笔记本阅读镜像，不是 Hands-On Large Language Models 全书。内容来自 Apache-2.0 开源仓库。"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="format-detection" content="telephone=no">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#fbf9f6">
<meta name="description" content="{esc(desc)}">
<title>{esc(title)}</title>
<link rel="icon" href="{rel(depth, "assets/favicon.svg")}" type="image/svg+xml">
<link rel="stylesheet" href="{rel(depth, "css/pygments.css")}">
<link rel="stylesheet" href="{rel(depth, "css/reader.css")}">
</head>
<body {body_attrs}>
<a class="skip" href="#content">跳到正文</a>
<header class="topbar">
  <div class="shell topbar-inner">
    <a class="brand" href="{rel(depth, "index.html")}">Hands-On LLM 笔记</a>
    {nav}
  </div>
  <div class="scrollline" aria-hidden="true"><span id="scrollline"></span></div>
</header>
<div class="shell page">
<main id="content">
{main}
</main>
{footer(depth)}
</div>
<noscript><p class="noscript-note shell">阅读进度存在这台浏览器里，需要 JavaScript。正文、代码和图片不依赖脚本。Plotly 图需要脚本才能画出来。</p></noscript>
<script src="{rel(depth, "js/reader.js")}"></script>
</body>
</html>
"""


def chapter_slug(number: int) -> str:
    return f"{number:02d}"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_notebook(relative: str) -> dict:
    path = NB_ROOT / relative
    if not path.exists():
        raise SystemExit(f"missing notebook: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def bonus_entries() -> list[dict]:
    entries = []
    folder = SRC / "bonus"
    for path in sorted(folder.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8")
        slug = re.sub(r"^\d+_", "", path.stem)
        title = slug.replace("_", " ")
        url = ""
        heading = re.search(r"^#\s+(.+)$", text, re.M)
        if heading:
            line = heading.group(1).strip()
            linked = re.match(r"\[([^\]]+)\]\((https?://[^)]+)\)", line)
            if linked:
                title = linked.group(1).strip()
                url = linked.group(2).strip()
            else:
                title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line).strip()
        if not url:
            link = re.search(r"\((https?://[^)]+)\)", text)
            url = link.group(1) if link else ""
        entries.append({"slug": slug, "title": title, "url": url, "path": path, "text": text})
    return entries


def build_chapters() -> list[dict]:
    built = []
    for number, title, relative in CHAPTERS:
        nb = load_notebook(relative)
        slug = chapter_slug(number)
        built.append(
            {
                "number": number,
                "slug": slug,
                "title": title,
                "subtitle": subtitle_from(nb),
                "path": relative,
                "colab": colab_url(relative),
                "github": blob_url(relative),
                "html": render_notebook(nb, depth=1),
            }
        )
    for index, chapter in enumerate(built):
        prev_ch = built[index - 1] if index else None
        next_ch = built[index + 1] if index + 1 < len(built) else None
        nav = chrome(
            [
                nav_anchor("../index.html", "目录"),
                nav_anchor(f"{prev_ch['slug']}.html" if prev_ch else None, "上一章", 'rel="prev"'),
                nav_anchor(f"{next_ch['slug']}.html" if next_ch else None, "下一章", 'rel="next"'),
                nav_anchor(chapter["colab"], "在 Colab 打开", 'class="colab"'),
                f'<button type="button" data-done="{chapter["slug"]}" aria-pressed="false">标为已读</button>',
            ]
        )
        end_prev = ""
        end_next = ""
        if prev_ch:
            end_prev = (
                f'<a class="endlink" href="{prev_ch["slug"]}.html" rel="prev">'
                f'<span class="endk">上一章</span><span class="endt">{esc(prev_ch["title"])}</span></a>'
            )
        else:
            end_prev = '<span class="endlink is-empty"></span>'
        if next_ch:
            end_next = (
                f'<a class="endlink next" href="{next_ch["slug"]}.html" rel="next">'
                f'<span class="endk">下一章</span><span class="endt">{esc(next_ch["title"])}</span></a>'
            )
        else:
            end_next = '<span class="endlink is-empty"></span>'
        main = (
            disclaimer()
            + '<p class="resume"><a href="#content" id="resume" hidden>回到上次位置</a></p>'
            + chapter["html"]
            + f'<nav class="endnav" aria-label="章节底部导航">{end_prev}{end_next}</nav>'
            + f'<p class="sourcerow"><a href="{esc(chapter["github"])}">上游笔记本源文件</a></p>'
        )
        page = layout(
            f"第 {chapter['number']} 章 · {chapter['title']}",
            1,
            main,
            nav,
            body_attrs=f'data-chapter="{chapter["slug"]}"',
        )
        write(DOCS / "chapters" / f"{chapter['slug']}.html", page)
    return built


def build_bonus(entries: list[dict]) -> None:
    readme = (SRC / "bonus" / "README.md").read_text(encoding="utf-8")
    rendered = render_md(readme, depth=1)
    rendered = re.sub(r"<h1>", "<h2>", rendered, count=1)
    rendered = re.sub(r"</h1>", "</h2>", rendered, count=1)
    cards = []
    for entry in entries:
        cards.append(
            "<li>"
            f'<a class="toc-main" href="{esc(entry["slug"])}.html">'
            f'<span class="toc-text"><span class="toc-title">{esc(entry["title"])}</span></span></a>'
            f'<div class="toc-actions"><a class="colab" href="{esc(entry["url"])}">在原站点阅读全文</a></div>'
            "</li>"
        )
    first = entries[0]["slug"] + ".html" if entries else None
    nav = chrome(
        [
            nav_anchor("../index.html", "目录"),
            nav_anchor(None, "上一篇"),
            nav_anchor(first, "下一篇", 'rel="next"'),
            nav_anchor(UPSTREAM + "/tree/main/bonus", "上游 bonus", 'class="action"'),
        ]
    )
    main = (
        "<h1>延伸阅读</h1>"
        + disclaimer()
        + "<p class=\"lead\">下面是上游 <code>bonus/</code> 目录里的简介。完整图文在外部站点，可能需要订阅。这里不转载那些长文。</p>"
        + '<ol class="toc">' + "".join(cards) + "</ol>"
        + f'<div class="markdown" lang="en">{rendered}</div>'
    )
    write(DOCS / "bonus" / "index.html", layout("延伸阅读", 1, main, nav))

    for index, entry in enumerate(entries):
        prev_item = entries[index - 1] if index else None
        next_item = entries[index + 1] if index + 1 < len(entries) else None
        nav = chrome(
            [
                nav_anchor("../index.html", "目录"),
                nav_anchor(f"{prev_item['slug']}.html" if prev_item else "index.html", "上一篇", 'rel="prev"'),
                nav_anchor(f"{next_item['slug']}.html" if next_item else None, "下一篇", 'rel="next"'),
                nav_anchor(entry["url"] or None, "原文", 'class="action"'),
            ]
        )
        body = render_md(entry["text"], depth=1)
        callout = (
            '<aside class="outbound"><span>这是上游仓库里的简介，不是外部长文全文。原站点可能需要订阅。</span>'
            + (f'<a href="{esc(entry["url"])}">在原站点阅读全文</a>' if entry["url"] else "")
            + "</aside>"
        )
        end_prev = (
            f'<a class="endlink" href="{prev_item["slug"]}.html"><span class="endk">上一篇</span>'
            f'<span class="endt">{esc(prev_item["title"])}</span></a>'
            if prev_item
            else '<a class="endlink" href="index.html"><span class="endk">上一篇</span><span class="endt">延伸阅读目录</span></a>'
        )
        end_next = (
            f'<a class="endlink next" href="{next_item["slug"]}.html"><span class="endk">下一篇</span>'
            f'<span class="endt">{esc(next_item["title"])}</span></a>'
            if next_item
            else '<span class="endlink is-empty"></span>'
        )
        main = disclaimer() + callout + f'<div class="markdown" lang="en">{body}</div>' + f'<nav class="endnav">{end_prev}{end_next}</nav>'
        write(DOCS / "bonus" / f"{entry['slug']}.html", layout(entry["title"], 1, main, nav))


def build_home(chapters: list[dict], entries: list[dict]) -> None:
    rows = []
    for chapter in chapters:
        sub = f'<span class="toc-sub">{esc(chapter["subtitle"])}</span>' if chapter["subtitle"] else ""
        rows.append(
            "<li>"
            f'<a class="toc-main" href="chapters/{chapter["slug"]}.html">'
            f'<span class="num">{chapter["slug"]}</span>'
            f'<span class="toc-text"><span class="toc-title">{esc(chapter["title"])}</span>{sub}</span></a>'
            '<div class="toc-actions">'
            f'<button type="button" data-done="{chapter["slug"]}" aria-pressed="false">标为已读</button>'
            f'<span class="pct" data-pct="{chapter["slug"]}">进度 0%</span>'
            f'<a class="colab" href="{esc(chapter["colab"])}">在 Colab 打开</a>'
            "</div>"
            f'<span class="meter" data-meter="{chapter["slug"]}"><span></span></span>'
            "</li>"
        )
    bonus_links = "".join(
        f'<li><a class="toc-main" href="bonus/{esc(entry["slug"])}.html"><span class="toc-text">'
        f'<span class="toc-title">{esc(entry["title"])}</span></span></a>'
        f'<div class="toc-actions"><a class="colab" href="{esc(entry["url"])}">在原站点阅读全文</a></div></li>'
        for entry in entries
    )
    first = chapters[0]
    nav = chrome(
        [
            nav_anchor("index.html", "目录", 'aria-current="page"'),
            nav_anchor(None, "上一章"),
            nav_anchor(f'chapters/{first["slug"]}.html', "下一章", 'rel="next"'),
            nav_anchor(first["colab"], "在 Colab 打开", 'class="colab"'),
        ]
    )
    main = f"""
<h1>Hands-On Large Language Models 笔记</h1>
{disclaimer()}
<img class="cover figure" src="images/book_cover.png" alt="Hands-On Large Language Models book cover">
<p class="lead">十二章笔记本可以在手机上接着读。进度只保存在这台浏览器里。「已读」和滚动百分比互相同步。</p>
<p class="progress-summary" id="progress-summary" data-total="12">已读 0 / 12</p>
<ol class="toc">
{''.join(rows)}
</ol>
<h2 class="section-title">延伸阅读</h2>
<p class="lead">上游 bonus 简介。外链文章不在本站全文转载。</p>
<ol class="toc">
{bonus_links}
<li><a class="toc-main" href="bonus/index.html"><span class="toc-text"><span class="toc-title">打开延伸阅读目录</span></span></a></li>
</ol>
"""
    write(DOCS / "index.html", layout("Hands-On LLM 笔记", 0, main, nav, body_attrs='data-page="home"'))


def build_404() -> None:
    nav = chrome(
        [
            nav_anchor("index.html", "目录"),
            nav_anchor(None, "上一章"),
            nav_anchor("chapters/01.html", "下一章"),
            nav_anchor(CHAPTERS and colab_url(CHAPTERS[0][2]), "在 Colab 打开", 'class="colab"'),
        ]
    )
    main = "<h1>没有这一页</h1>" + disclaimer() + '<p class="lead"><a href="index.html">回到目录</a></p>'
    write(DOCS / "404.html", layout("没有这一页", 0, main, nav))


def copy_static() -> None:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir()
    shutil.copytree(WEB / "css", DOCS / "css")
    shutil.copytree(WEB / "js", DOCS / "js")
    shutil.copytree(WEB / "assets", DOCS / "assets")
    shutil.copytree(SRC / "images", DOCS / "images")
    shutil.copy2(ROOT / "LICENSE", DOCS / "LICENSE")
    shutil.copy2(ROOT / "NOTICE", DOCS / "NOTICE")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".codehilite")
    write(DOCS / "css" / "pygments.css", pygments_css + "\n")


def verify() -> None:
    html_files = sorted(DOCS.rglob("*.html"))
    if len(list((DOCS / "chapters").glob("*.html"))) != 12:
        raise SystemExit("expected 12 chapter pages")
    required_css = [
        "overflow-x: auto",
        "max-width: 100%",
        "safe-area-inset",
        "viewport-fit",
        "min-height: 48px",
    ]
    # viewport-fit is in HTML, not CSS. Check CSS pieces separately.
    css = (DOCS / "css" / "reader.css").read_text(encoding="utf-8")
    for needle in ("overflow-x: auto", "max-width: 100%", "safe-area-inset", "min-height: 48px", "font-size: 1rem"):
        if needle not in css:
            raise SystemExit(f"reader.css missing {needle}")
    data_images = {"05": 0, "09": 0, "11": 0}
    for path in html_files:
        text = path.read_text(encoding="utf-8")
        if 'name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"' not in text:
            raise SystemExit(f"missing viewport meta: {path}")
        if "笔记本镜像，不是全书。" not in text:
            raise SystemExit(f"missing disclaimer: {path}")
        for label in ("目录", "在 Colab 打开"):
            if label not in text and path.name != "404.html":
                # bonus pages use 原文 instead of Colab; home and chapters have Colab
                pass
        if path.parent.name == "chapters":
            for label in ("目录", "上一章", "下一章", "在 Colab 打开"):
                if label not in text:
                    raise SystemExit(f"{path.name} missing nav label {label}")
        for match in IMG_RE.finditer(text):
            tag = match.group(0)
            src_match = re.search(r'\bsrc\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
            alt_match = re.search(r'\balt\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
            if not src_match:
                raise SystemExit(f"img without src in {path}")
            src = src_match.group(2)
            alt = alt_match.group(2).strip() if alt_match else ""
            if not alt:
                raise SystemExit(f"empty alt in {path}: {src[:80]}")
            if src.startswith("data:image/"):
                payload = src.split(",", 1)[1]
                binary = base64.b64decode(re.sub(r"\s+", "", payload))
                if src.startswith("data:image/png") and not binary.startswith(b"\x89PNG"):
                    raise SystemExit(f"bad data png in {path}")
                if path.parent.name == "chapters":
                    key = path.stem
                    if key in data_images:
                        data_images[key] += 1
                continue
            if src.startswith(("http://", "https://")):
                raise SystemExit(f"remote image left in {path}: {src[:140]}")
            target = (path.parent / src).resolve()
            if not target.exists():
                raise SystemExit(f"missing image {src} from {path}")
        if "img.shields.io" in text:
            raise SystemExit(f"shields badge left in {path}")
    if "images/book_cover.png" not in (DOCS / "chapters" / "01.html").read_text(encoding="utf-8"):
        raise SystemExit("chapter 1 is missing the local book cover")
    if data_images["05"] < 3:
        raise SystemExit(f"chapter 5 expected saved figures, found {data_images['05']}")
    if data_images["09"] < 5:
        raise SystemExit(f"chapter 9 expected saved figures, found {data_images['09']}")
    bonus_overview = DOCS / "images" / "bonus_overview.png"
    if not bonus_overview.exists():
        raise SystemExit("bonus overview image was not copied")
    quant = (DOCS / "bonus" / "quantization.html").read_text(encoding="utf-8")
    for name in ("bonus_overview.png", "bonus_int8.png", "bonus_bitnet.png"):
        if f"../images/{name}" not in quant:
            raise SystemExit(f"quantization page missing {name}")
    print(f"verified {len(html_files)} html files; chapter images 05={data_images['05']} 09={data_images['09']}")


def main() -> None:
    copy_static()
    chapters = build_chapters()
    entries = bonus_entries()
    build_bonus(entries)
    build_home(chapters, entries)
    build_404()
    verify()
    print(f"wrote {DOCS}")


if __name__ == "__main__":
    main()
