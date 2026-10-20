#!/usr/bin/env python3
"""Validate the single content source, render the book, and export readable Markdown."""
from __future__ import annotations

import argparse
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "book"
OUTPUT = BOOK / "_book"


def frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise ValueError(f"{path.relative_to(ROOT)} 缺少 YAML frontmatter")
    return yaml.safe_load(match[1]) or {}, text[match.end():]


def pages():
    return [BOOK / "index.qmd", *sorted((BOOK / "content").rglob("*.qmd"))]


class UniqueKeyLoader(yaml.SafeLoader):
    """Redirect aliases must not silently overwrite an earlier YAML entry."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        try:
            if key in result:
                raise ValueError(f"redirects.yml 包含重复键：{key}")
            result[key] = loader.construct_object(value_node)
        except TypeError as exc:
            raise ValueError("redirects.yml 的键必须是路径字符串") from exc
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def safe_article_path(value):
    """Accept canonical, unescaped book-relative qmd paths only."""
    if (not isinstance(value, str) or not value or "\\" in value
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError(f"redirects.yml 包含不安全文章路径：{value!r}")
    parsed = urlsplit(value)
    path = PurePosixPath(value)
    if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or path.is_absolute()
            or ".." in path.parts or str(path) != value or path.suffix != ".qmd"
            or unquote(value) != value or not (BOOK / value).resolve().is_relative_to(BOOK.resolve())):
        raise ValueError(f"redirects.yml 包含不安全文章路径：{value!r}")
    return value


def load_redirects():
    """Read legacy aliases, validating them before any output is written."""
    path = BOOK / "redirects.yml"
    if not path.exists():
        return {}
    try:
        config = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"redirects.yml 不是合法 YAML：{exc}") from exc
    if (not isinstance(config, dict) or set(config) != {"schema_version", "redirects"}
            or type(config.get("schema_version")) is not int or config["schema_version"] != 1
            or not isinstance(config.get("redirects"), dict)):
        raise ValueError("redirects.yml 必须使用 schema_version: 1 和 redirects 路径映射")
    redirects = {safe_article_path(old): safe_article_path(new) for old, new in config["redirects"].items()}
    current = {source.relative_to(BOOK).as_posix() for source in pages()}
    for old, new in redirects.items():
        if old in current or (BOOK / old).exists():
            raise ValueError(f"兼容跳转源路径与当前文章冲突：{old}")
        if new in redirects:
            raise ValueError(f"兼容跳转不能形成跳转链或循环：{old} → {new}")
        if new not in current or not (BOOK / new).is_file():
            raise ValueError(f"兼容跳转目标不是当前文章：{old} → {new}")
    return redirects


def redirect_outputs(suffix):
    base = OUTPUT / "markdown" if suffix == ".md" else OUTPUT
    return {
        (base / Path(old).with_suffix(suffix)).resolve(): (base / Path(new).with_suffix(suffix)).resolve()
        for old, new in load_redirects().items()
    }


def relative_url(target, parent):
    return quote(Path(os.path.relpath(Path(target).resolve(), start=Path(parent).resolve())).as_posix(), safe="/")


def rewrite_markdown_url(url, source, destination):
    """Resolve each authored URL, then express it from the actual exported file."""
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return url
    decoded = unquote(parsed.path)
    local = ((BOOK / decoded.lstrip("/")) if decoded.startswith("/") else source.parent / decoded).resolve()
    if not local.is_relative_to(BOOK.resolve()):
        raise ValueError(f"{source}: 链接超出 book 目录：{url}")
    relative = local.relative_to(BOOK.resolve())
    if local.suffix == ".qmd":
        output = OUTPUT / "markdown" / relative.with_suffix(".md")
    else:
        output = OUTPUT / relative
    return urlunsplit(("", "", relative_url(output, destination.parent), parsed.query, parsed.fragment))


def chapters(node):
    if isinstance(node, str) and node.endswith(".qmd"):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from chapters(item)
    elif isinstance(node, dict):
        yield from chapters(node.get("chapters", []))


def giscus_settings(config):
    values = {name: os.environ.get(name, "") for name in
              ("GISCUS_REPO_ID", "GISCUS_CATEGORY_ID", "GISCUS_CATEGORY")}
    if not any(values.values()):
        return None
    if any(value != value.strip() for value in values.values()):
        raise ValueError("Giscus 配置值不能含首尾空白")
    if not values["GISCUS_REPO_ID"] or not values["GISCUS_CATEGORY_ID"]:
        raise ValueError("启用 Giscus 必须同时设置 GISCUS_REPO_ID 和 GISCUS_CATEGORY_ID")
    return {
        "data-repo": config["guide-repo"].removeprefix("https://github.com/"),
        "data-repo-id": values["GISCUS_REPO_ID"],
        "data-category": values["GISCUS_CATEGORY"] or "文章评论",
        "data-category-id": values["GISCUS_CATEGORY_ID"],
        "data-mapping": "specific",
        "data-strict": "1",
        "data-lang": "zh-CN",
        "data-theme": "light",
    }


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, cwd=ROOT, **kwargs)


def pandoc_json(quarto, path):
    result = run([quarto, "pandoc", path, "--from=markdown", "--to=json"], capture_output=True, text=True)
    return json.loads(result.stdout)


def validate_ast(node, path, known_authors, attributed=False):
    """Check actual parsed blocks, including nested lists and figure captions."""
    if isinstance(node, list):
        for child in node:
            validate_ast(child, path, known_authors, attributed)
        return
    if not isinstance(node, dict):
        return
    kind, content = node.get("t"), node.get("c")
    if kind == "Div":
        attr, children = content
        if "contribution" in attr[1]:
            fields = dict(attr[2])
            if not fields.get("authors", "").strip():
                raise ValueError(f"{path}: 署名内容块缺少 authors")
            for field in ("authors", "contributors"):
                for author in filter(None, (x.strip() for x in fields.get(field, "").split(","))):
                    if author not in known_authors:
                        raise ValueError(f"{path}: 未注册作者 {author}")
            attributed = True
        validate_ast(children, path, known_authors, attributed)
        return
    if kind in {"Para", "Plain", "CodeBlock", "Table", "Figure"} and not attributed:
        raise ValueError(f"{path}: 存在未归入署名内容块的 {kind}")
    if kind in {"RawBlock", "RawInline"} and content[0] in {"latex", "tex"}:
        raise ValueError(f"{path}: 尚有未转换的 LaTeX: {content[1][:100]}")
    if kind in {"Image", "Link"}:
        target = content[-1][0]
        parsed = urlsplit(target)
        if not parsed.scheme and not parsed.netloc and parsed.path:
            local = (BOOK / parsed.path.lstrip("/")) if parsed.path.startswith("/") else path.parent / unquote(parsed.path)
            if parsed.path.endswith(".qmd") and not local.exists():
                raise ValueError(f"{path}: 正文链接不存在 {target}")
            if kind == "Image" and not local.exists():
                raise ValueError(f"{path}: 插图不存在 {target}")
    if kind == "Header":
        if content[0] == 1:
            raise ValueError(f"{path}: 标题由 frontmatter 生成，正文不要重复写一级标题")
        return  # Headings are navigation rather than independently authored paragraphs.
    for child in node.values():
        validate_ast(child, path, known_authors, attributed)


def validate_sources(quarto):
    config = yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8"))
    giscus_settings(config)  # Reject incomplete service configuration before rendering.
    load_redirects()
    known = yaml.safe_load((BOOK / "_authors.yml").read_text(encoding="utf-8"))["guide-authors"]
    listed = list(chapters(config["book"]["chapters"]))
    actual = [str(p.relative_to(BOOK)) for p in pages()]
    if len(listed) != len(set(listed)) or set(listed) != set(actual):
        raise ValueError(f"目录与正文不一致：未列入 {set(actual)-set(listed)}，缺失 {set(listed)-set(actual)}")
    discussion_ids = set()
    for path in pages():
        meta, body = frontmatter(path)
        if not isinstance(meta.get("title"), str) or not meta["title"].strip():
            raise ValueError(f"{path}: 缺少文章标题")
        identifier = meta.get("discussion-id", "")
        if not re.fullmatch(r"xp-guide-[a-z0-9-]+", identifier) or identifier in discussion_ids:
            raise ValueError(f"{path}: discussion-id 缺失、重复或不合法")
        discussion_ids.add(identifier)
        if f"{{#{identifier}}}" not in body:
            raise ValueError(f"{path}: 缺少与 discussion-id 同名的稳定页首锚点")
        if not body.strip():
            raise ValueError(f"{path}: 正文为空")
        ast = pandoc_json(quarto, path)
        validate_ast(ast["blocks"], path, known)
    print(f"正文检查通过：{len(actual)} 页，署名覆盖、作者名单、目录与讨论标识有效。", flush=True)


def export_markdown(quarto):
    destination = OUTPUT / "markdown"
    entries = []
    search_records = []
    for path in pages():
        meta, _ = frontmatter(path)
        relative = path.relative_to(BOOK).with_suffix(".md")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        def rewrite_nodes(node):
            if isinstance(node, list):
                for child in node:
                    rewrite_nodes(child)
            elif isinstance(node, dict):
                if node.get("t") in {"Image", "Link"}:
                    node["c"][-1][0] = rewrite_markdown_url(node["c"][-1][0], path, target)
                for child in node.values():
                    rewrite_nodes(child)
        ast = pandoc_json(quarto, path)
        rewrite_nodes(ast["blocks"])
        result = run([
            quarto, "pandoc", "--from=json", "--to=gfm", "--wrap=none",
            f"--metadata-file={BOOK / '_authors.yml'}",
            f"--lua-filter={BOOK / 'filters/markdown-export.lua'}",
            f"--lua-filter={BOOK / 'filters/attribution.lua'}",
        ], input=json.dumps(ast), capture_output=True, text=True)
        text = result.stdout
        if not re.search(r"^# ", text, re.M):
            text = f"# {meta['title']}\n\n" + text
        target.write_text(text, encoding="utf-8")
        entries.append((str(relative), meta["title"]))
        # The native HTML index includes disclosure text once per paragraph and
        # mistakes the participation footer for an article summary. Index the
        # authored AST instead, keeping the existing Quarto search interface.
        plain = run([quarto, "pandoc", "--from=json", "--to=plain", "--wrap=none"],
                    input=json.dumps(ast), capture_output=True, text=True).stdout.strip()
        href = str(path.relative_to(BOOK).with_suffix(".html"))
        search_records.append({"objectID": href, "href": href, "title": meta["title"],
                               "section": "", "text": plain})
    index = ["# 西浦博士生非官方攻略", "", "与网页和 PDF 共用正文源。署名以普通文字保留；历史归属待确认不代表已经逐段核实。", "", "## 文章", ""]
    for relative, title in entries:
        index.append(f"- [{title}](markdown/{relative})")
    (OUTPUT / "llms.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    (OUTPUT / "search.json").write_text(json.dumps(search_records, ensure_ascii=False), encoding="utf-8")
    # GitHub Pages must copy leading-underscore Quarto assets without Jekyll.
    (OUTPUT / ".nojekyll").touch()
    print(f"纯 Markdown 导出完成：{len(entries)} 页。", flush=True)


def export_redirects():
    redirects = load_redirects()
    if not redirects:
        return
    config = yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8"))
    site = config.get("guide-site", "")
    if not isinstance(site, str) or urlsplit(site).scheme not in {"http", "https"} or not urlsplit(site).netloc:
        raise ValueError("生成兼容跳转需要合法的 guide-site 绝对网址")
    # Never overwrite a rendered article or attachment, even if its route was not
    # listed in the book's table of contents.
    outputs = [path for suffix in (".html", ".md") for path in redirect_outputs(suffix)]
    for path in outputs:
        if path.exists():
            raise ValueError(f"兼容跳转不能覆盖已生成文件：{path.relative_to(OUTPUT)}")
    for old, new in redirects.items():
        html_file = OUTPUT / Path(old).with_suffix(".html")
        new_html = OUTPUT / Path(new).with_suffix(".html")
        target = relative_url(new_html, html_file.parent)
        canonical = site.rstrip("/") + "/" + quote(Path(new).with_suffix(".html").as_posix(), safe="/")
        title = frontmatter(BOOK / new)[0]["title"]
        html_file.parent.mkdir(parents=True, exist_ok=True)
        html_file.write_text(
            '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>文章已迁移：{escape(title)}</title>\n'
            f'<link rel="canonical" href="{escape(canonical, quote=True)}">\n'
            '</head><body>\n<h1>文章已迁移</h1>\n'
            f'<p>请前往新地址阅读：<a href="{escape(target, quote=True)}">{escape(title)}</a>。</p>\n'
            '<script>\n'
            f'const target = new URL({json.dumps(target)}, window.location.href);\n'
            'target.search = window.location.search;\n'
            'target.hash = window.location.hash;\n'
            'window.location.replace(target.href);\n'
            '</script>\n</body></html>\n', encoding="utf-8")
        markdown_file = OUTPUT / "markdown" / Path(old).with_suffix(".md")
        new_markdown = OUTPUT / "markdown" / Path(new).with_suffix(".md")
        markdown_file.parent.mkdir(parents=True, exist_ok=True)
        markdown_file.write_text(
            f'# 文章已迁移\n\n请前往新地址阅读：[当前文章]({relative_url(new_markdown, markdown_file.parent)})。\n',
            encoding="utf-8")
    print(f"兼容路径导出完成：{len(redirects)} 个 HTML 跳转与 Markdown 迁移提示。", flush=True)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()
        self.duplicate_ids = set()
        self.giscus_scripts = []
    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if fields.get("id"):
            if fields["id"] in self.ids:
                self.duplicate_ids.add(fields["id"])
            self.ids.add(fields["id"])
        if tag in {"a", "img", "script", "link"}:
            for key in ("href", "src"):
                if fields.get(key):
                    self.urls.append(fields[key])
        if tag == "script" and fields.get("src") == "https://giscus.app/client.js":
            self.giscus_scripts.append(fields)


def validate_output(html_only):
    config = yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8"))
    giscus = giscus_settings(config)
    articles = {(OUTPUT / source.relative_to(BOOK).with_suffix(".html")).resolve() for source in pages()}
    redirects = redirect_outputs(".html")
    discussions = {
        (OUTPUT / source.relative_to(BOOK).with_suffix(".html")).resolve(): frontmatter(source)[0]["discussion-id"]
        for source in pages()
    } if giscus else {}
    documents = {}
    for path in OUTPUT.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text(encoding="utf-8"))
        documents[path.resolve()] = parser
    errors = set()
    expected = articles | set(redirects)
    for path in expected - set(documents):
        errors.add(f"缺少{'文章' if path in articles else '兼容跳转'}：{path.relative_to(OUTPUT)}")
    for path in set(documents) - expected:
        errors.add(f"存在未登记的 HTML：{path.relative_to(OUTPUT)}")
    for path, parser in documents.items():
        for identifier in parser.duplicate_ids:
            errors.add(f"{path.relative_to(OUTPUT)} → 重复锚点 {identifier}")
        for url in parser.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or url.startswith("//"):
                continue
            decoded = unquote(parts.path)
            if html_only and decoded.endswith("xp-pgrs-unofficial-guide.pdf"):
                continue
            if decoded.startswith("/"):
                decoded = decoded.removeprefix("/xp_pgrs_unofficial_guide/").lstrip("/")
                target = OUTPUT / decoded
            else:
                target = path.parent / decoded if decoded else path
            target = target.resolve()
            if target.is_dir():
                target /= "index.html"
            if not target.is_relative_to(OUTPUT.resolve()) or not target.exists():
                errors.add(f"{path.relative_to(OUTPUT)} → {url}")
            # An old HTML URL redirects with its fragment intact. Check that
            # fragment on the current article rather than on its tiny stub.
            elif (parts.fragment and redirects.get(target, target) in documents
                  and unquote(parts.fragment) not in documents[redirects.get(target, target)].ids):
                errors.add(f"{path.relative_to(OUTPUT)} → 锚点不存在 {url}")
        if path in redirects and parser.giscus_scripts:
            errors.add(f"{path.relative_to(OUTPUT)} 的兼容跳转不应包含 Giscus 讨论区")
        if giscus and path in articles:
            label = path.relative_to(OUTPUT)
            if len(parser.giscus_scripts) != 1:
                errors.add(f"{label} 必须包含一个独立 Giscus 讨论区")
            elif path not in discussions:
                errors.add(f"{label} 的 Giscus 讨论区没有对应的源文章")
            else:
                expected = {**giscus, "data-term": discussions[path]}
                for field, value in expected.items():
                    if parser.giscus_scripts[0].get(field) != value:
                        errors.add(f"{label} 的 Giscus {field} 与配置或文章 discussion-id 不一致")
    if errors:
        raise ValueError("产物链接检查失败：\n" + "\n".join(sorted(errors)))
    if not html_only and not (OUTPUT / "xp-pgrs-unofficial-guide.pdf").exists():
        raise ValueError("未生成整本 PDF")
    search = json.loads((OUTPUT / "search.json").read_text(encoding="utf-8"))
    if len(search) != len(pages()) or any("一起完善这一页" in entry["text"] for entry in search):
        raise ValueError("搜索索引不完整或混入供稿控件文本")
    print(f"产物检查通过：{len(articles)} 篇 HTML 文章、{len(redirects)} 个兼容跳转，本地链接和锚点有效。", flush=True)


def validate_markdown(quarto):
    articles = {(OUTPUT / "markdown" / source.relative_to(BOOK).with_suffix(".md")).resolve() for source in pages()}
    redirects = redirect_outputs(".md")
    documents = {}
    for path in (OUTPUT / "markdown").rglob("*.md"):
        result = run([quarto, "pandoc", path, "--from=gfm", "--to=json"], capture_output=True, text=True)
        ast = json.loads(result.stdout)
        parser = Links()
        def inspect(node):
            if isinstance(node, list):
                for child in node:
                    inspect(child)
            elif isinstance(node, dict):
                kind, content = node.get("t"), node.get("c")
                if kind in {"Link", "Image"}:
                    parser.urls.append(content[-1][0])
                elif kind == "Header":
                    parser.ids.add(content[1][0])
                elif kind in {"RawBlock", "RawInline"} and content[0] == "html":
                    parser.feed(content[1])
                for child in node.values():
                    inspect(child)
        inspect(ast["blocks"])
        documents[path.resolve()] = parser
    errors = set()
    expected = articles | set(redirects)
    for path in expected - set(documents):
        errors.add(f"缺少{'文章' if path in articles else '迁移提示'}：{path.relative_to(OUTPUT)}")
    for path in set(documents) - expected:
        errors.add(f"存在未登记的 Markdown：{path.relative_to(OUTPUT)}")
    for path, parser in documents.items():
        for url in parser.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not url or parts.path.startswith("/"):
                continue
            target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
            if not target.is_relative_to(OUTPUT.resolve()) or not target.exists():
                errors.add(f"{path.relative_to(OUTPUT)} → {url}")
            elif parts.fragment and target in documents and unquote(parts.fragment) not in documents[target].ids:
                errors.add(f"{path.relative_to(OUTPUT)} → 锚点不存在 {url}")
    if errors:
        raise ValueError("Markdown 链接检查失败：\n" + "\n".join(sorted(errors)))
    print(f"Markdown 检查通过：{len(articles)} 篇文章、{len(redirects)} 个迁移提示，图片、文件链接与显式锚点有效。", flush=True)


def validate_pdf():
    from pypdf import PdfReader
    reader = PdfReader(OUTPUT / "xp-pgrs-unofficial-guide.pdf")
    destinations = reader.named_destinations
    errors, internal = set(), 0
    for number, page in enumerate(reader.pages, 1):
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            action = annotation.get("/A", {})
            if hasattr(action, "get_object"):
                action = action.get_object()
            uri = str(action.get("/URI", ""))
            if uri and (".qmd" in uri or not urlsplit(uri).scheme):
                errors.add(f"第 {number} 页残留本地链接 {uri}")
            if action.get("/S") == "/GoToR":
                errors.add(f"第 {number} 页依赖未随 PDF 分发的外部文件")
            destination = annotation.get("/Dest")
            if action.get("/S") == "/GoTo":
                destination = action.get("/D")
            if isinstance(destination, str):
                internal += 1
                if destination not in destinations:
                    errors.add(f"第 {number} 页内部目的地不存在 {destination}")
    if errors:
        raise ValueError("PDF 链接检查失败：\n" + "\n".join(sorted(errors)))
    print(f"PDF 检查通过：{len(reader.pages)} 页，{internal} 个内部链接有效，附件使用在线绝对地址。", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-only", action="store_true", help="快速预览，仅生成网页与 Markdown")
    parser.add_argument("--check-only", action="store_true", help="只校验正文与署名，不渲染")
    args = parser.parse_args()
    quarto = os.environ.get("QUARTO") or shutil.which("quarto")
    if not quarto:
        raise ValueError("找不到 Quarto。请安装 1.10.19，或设置 QUARTO=/path/to/quarto。")
    validate_sources(quarto)
    if args.check_only:
        return
    # Clean generated output only; never edit the authored qmd or the LaTeX archive.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    run([quarto, "render", BOOK, "--to", "html" if args.html_only else "all"])
    export_markdown(quarto)
    export_redirects()
    validate_output(args.html_only)
    validate_markdown(quarto)
    if not args.html_only:
        validate_pdf()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"构建失败：{exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(1)
