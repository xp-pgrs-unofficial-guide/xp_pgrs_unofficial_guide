#!/usr/bin/env python3
"""Validate the single content source, render the book, and export readable Markdown."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, quote, unquote, urlsplit, urlunsplit

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
    result = []
    for root in language_roots():
        result.extend([root / "index.qmd", *sorted((root / "content").rglob("*.qmd")),
                       *sorted((root / "authors").rglob("*.qmd"))])
    return result


def language_roots():
    english = BOOK / "en"
    has_english = ((english / "index.qmd").exists()
                   or any((english / "content").rglob("*.qmd"))
                   or any((english / "authors").rglob("*.qmd")))
    return [BOOK, *([english] if has_english else [])]


def source_root(path):
    return BOOK / "en" if path.resolve().is_relative_to((BOOK / "en").resolve()) else BOOK


def locale_output(root):
    return OUTPUT if root == BOOK else OUTPUT / "en"


def markdown_output(path):
    root = source_root(path)
    return locale_output(root) / "markdown" / path.relative_to(root).with_suffix(".md")


def prepare_english_config():
    """Derive the English project from shared settings instead of maintaining two copies."""
    if len(language_roots()) == 1:
        return
    base = yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8"))
    translations = yaml.safe_load((BOOK / "_languages.yml").read_text(encoding="utf-8"))
    config = deepcopy(base)
    config["project"]["output-dir"] = "../_book/en"
    config["project"].pop("resources", None)
    config["book"].update(translations.get("book", {}))
    config["book"]["site-url"] = base["guide-site"].rstrip("/") + "/en/"
    config["book"]["repo-subdir"] = "book/en"
    def translate_parts(node):
        if isinstance(node, list):
            for item in node:
                translate_parts(item)
        elif isinstance(node, dict):
            if "part" in node:
                node["part"] = translations.get("parts", {}).get(node["part"], node["part"])
            translate_parts(node.get("chapters", []))
    translate_parts(config["book"]["chapters"])
    config["lang"] = translations.get("lang", "en")
    config["metadata-files"] = ["../_authors.yml"]
    config["filters"] = ["../" + path for path in base.get("filters", [])]
    config["guide-language"] = "en"
    config["guide-source-prefix"] = "en/"
    config["guide-site-root"] = base["guide-site"]
    config["guide-site"] = config["book"]["site-url"]
    html = config.setdefault("format", {}).setdefault("html", {})
    html["css"] = "../assets/guide.css"
    html["toc-title"] = "On this page"
    pdf = config["format"].setdefault("pdf", {})
    pdf["classoption"] = [option for option in pdf.get("classoption", []) if not str(option).startswith("scheme=")] + ["scheme=plain"]
    pdf["include-in-header"] = "../pdf/style.tex"
    pdf["template-partials"] = ["../pdf/before-body.tex"]
    config["guide-english"] = True
    config["guide-pdf-cover"] = "../pdf/cover.jpg"
    (BOOK / "en/_quarto.yml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")


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


class AuthorMetadataLoader(yaml.SafeLoader):
    """Reject duplicate author IDs and fields before YAML can overwrite them."""

    def construct_mapping(self, node, deep=False):
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("_authors.yml 的键必须是字符串")
            if key in keys:
                raise ValueError(f"_authors.yml 包含重复键：{key}")
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def load_author_metadata():
    """Validate optional public profiles alongside the stable bilingual name maps."""
    try:
        config = yaml.load((BOOK / "_authors.yml").read_text(encoding="utf-8"), Loader=AuthorMetadataLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"_authors.yml 不是合法 YAML：{exc}") from exc
    allowed = {"guide-authors", "guide-authors-en", "guide-author-profiles"}
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError("_authors.yml 只能包含作者姓名映射和 guide-author-profiles")
    names = config.get("guide-authors")
    if not isinstance(names, dict) or not names:
        raise ValueError("_authors.yml 缺少非空 guide-authors 映射")
    for field in ("guide-authors", "guide-authors-en"):
        if field not in config:
            continue  # Preserve existing single-language projects without profile metadata.
        mapping = config[field]
        if not isinstance(mapping, dict) or set(mapping) != set(names):
            raise ValueError("_authors.yml 中英文作者 ID 名单不一致")
        for identifier, name in mapping.items():
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", identifier):
                raise ValueError(f"_authors.yml 作者 ID 不合法：{identifier}")
            if not isinstance(name, str) or not name.strip() or name != name.strip() or "\n" in name:
                raise ValueError(f"_authors.yml {field}.{identifier} 必须是非空姓名字符串")
    profiles = config.get("guide-author-profiles", {})
    if not isinstance(profiles, dict) or set(profiles) - set(names):
        raise ValueError("_authors.yml guide-author-profiles 必须是已注册作者 ID 的资料映射")
    localized_text = ("affiliation", "department", "bio")
    localized_lists = ("research-interests", "project-roles")
    links = ("google-scholar", "website", "github", "institutional-profile")
    fields = {"type", "orcid", "email", *links}
    for field in (*localized_text, *localized_lists):
        fields.update((field, field + "-en"))
    for identifier, profile in profiles.items():
        prefix = f"_authors.yml guide-author-profiles.{identifier}"
        if not isinstance(profile, dict) or set(profile) - fields:
            raise ValueError(f"{prefix} 必须是资料映射且不能包含未知字段")
        kind = profile.get("type", "person")
        if kind not in ("person", "team", "placeholder"):
            raise ValueError(f"{prefix}.type 必须为 person、team 或 placeholder")
        for field in (*localized_text, *localized_lists):
            if (field in profile) != (field + "-en" in profile):
                raise ValueError(f"{prefix}.{field} 必须同时提供中英文字段")
            for key in (field, field + "-en"):
                if key not in profile:
                    continue
                content = profile[key]
                if field in localized_lists:
                    if (not isinstance(content, list) or not content or
                            any(not isinstance(item, str) or not item.strip() or item != item.strip() for item in content)):
                        raise ValueError(f"{prefix}.{key} 必须是非空字符串列表")
                elif not isinstance(content, str) or not content.strip() or content != content.strip():
                    raise ValueError(f"{prefix}.{key} 必须是非空字符串")
            if field in localized_lists and field in profile and len(profile[field]) != len(profile[field + "-en"]):
                raise ValueError(f"{prefix}.{field} 中英文列表条目数必须一致")
        if kind != "person" and any(field in profile for field in ("orcid", "google-scholar")):
            raise ValueError(f"{prefix} 团队或占位身份不能填写个人 ORCID／Google Scholar")
        if "email" in profile:
            email = profile["email"]
            domain_label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
            email_pattern = rf"[A-Za-z0-9_+-]+(?:\.[A-Za-z0-9_+-]+)*@{domain_label}(?:\.{domain_label})+"
            if (not isinstance(email, str) or len(email) > 254 or
                    not re.fullmatch(email_pattern, email) or len(email.split("@")[0]) > 64):
                raise ValueError(f"{prefix}.email 必须是有效的裸邮箱地址，不含 mailto:、空白或查询参数")
        if "orcid" in profile:
            orcid = profile["orcid"]
            if not isinstance(orcid, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]", orcid):
                raise ValueError(f"{prefix}.orcid 必须是带连字符的 16 位 ORCID 标识")
            digits = orcid.replace("-", "")
            total = 0
            # ORCID's published ISO 7064 MOD 11-2 checksum, including final X.
            for digit in digits[:-1]:
                total = (total + int(digit)) * 2
            checksum = (12 - total % 11) % 11
            if digits[-1] != ("X" if checksum == 10 else str(checksum)):
                raise ValueError(f"{prefix}.orcid 校验位不正确")
        for field in links:
            if field not in profile:
                continue
            address = profile[field]
            message = f"{prefix}.{field} 必须是有效的 HTTPS 公开主页链接"
            if (not isinstance(address, str) or not address or "\\" in address or
                    any(ord(character) <= 32 or ord(character) == 127 for character in address)):
                raise ValueError(message)
            try:
                parsed = urlsplit(address)
                if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None
                        or parsed.port not in (None, 443) or "%" in parsed.netloc):
                    raise ValueError(message)
            except ValueError as exc:
                raise ValueError(message) from exc
            if field == "google-scholar":
                users = parse_qs(parsed.query, keep_blank_values=True).get("user", [])
                if (parsed.hostname != "scholar.google.com" or parsed.path != "/citations"
                        or len(users) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]+", users[0])):
                    raise ValueError(f"{prefix}.google-scholar 必须是含唯一 user ID 的 Google Scholar 个人主页")
            if field == "github" and (parsed.hostname != "github.com" or
                    not re.fullmatch(r"/[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/?", parsed.path)):
                raise ValueError(f"{prefix}.github 必须指向 GitHub 用户或组织主页")
    return config


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
        output = markdown_output(local)
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
        # A part may itself be a source page. It appears once as the clickable
        # parent in Quarto's sidebar, rather than again as its own child chapter.
        yield from chapters(node.get("part"))
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
        "data-reactions-enabled": "1",
        "data-emit-metadata": "0",
        "data-input-position": "top",
        "data-loading": "lazy",
        "data-lang": "en" if str(config.get("lang", "")).startswith("en") else "zh-CN",
        "data-theme": "preferred_color_scheme",
    }


def run(command, **kwargs):
    command = [str(x) for x in command]
    # Allow the same-version native Pandoc to bypass a failing local Quarto
    # launcher. Quarto still renders the books and remains the default.
    if len(command) > 1 and command[1] == "pandoc" and os.environ.get("PANDOC_BIN"):
        command = [os.environ["PANDOC_BIN"], *command[2:]]
    return subprocess.run(command, check=True, cwd=ROOT, **kwargs)


def pandoc_json(quarto, path):
    command = [quarto, "pandoc", path, "--from=markdown", "--to=json"]
    meta, _ = frontmatter(path)
    if meta.get("guide-author-id") or meta.get("guide-author-index"):
        root = source_root(path)
        command.extend([f"--metadata-file={root / '_quarto.yml'}",
                        f"--metadata-file={BOOK / '_authors.yml'}",
                        f"--metadata=guide-source-root:{root}",
                        f"--lua-filter={BOOK / 'filters/author-pages.lua'}"])
    result = run(command, capture_output=True, text=True)
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


def contribution_signatures(ast):
    result = []
    def visit(node):
        if isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, dict):
            if node.get("t") == "Div" and "contribution" in node["c"][0][1]:
                fields = dict(node["c"][0][2])
                result.append(tuple(fields.get(key, "") for key in ("authors", "contributors", "status")))
            for child in node.values():
                visit(child)
    visit(ast["blocks"])
    return result


def header_signatures(ast):
    result = []
    def visit(node):
        if isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, dict):
            if node.get("t") == "Header":
                result.append((node["c"][0], node["c"][1][0]))
            for child in node.values():
                visit(child)
    visit(ast["blocks"])
    return result


def validate_translation(source, translation, source_ast, translated_ast):
    original, body = frontmatter(source)
    meta, translated_body = frontmatter(translation)
    expected = source.relative_to(BOOK).as_posix()
    if meta.get("lang") != "en":
        raise ValueError(f"{translation}: 英文页面必须设置 lang: en")
    if meta.get("translation-source") != expected:
        raise ValueError(f"{translation}: translation-source 应为 {expected}")
    if meta.get("translation-source-sha256") != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError(f"{translation}: 英文译文已过期；请核对中文变化并更新 translation-source-sha256")
    if meta.get("translation-status") not in {"draft", "reviewed"}:
        raise ValueError(f"{translation}: translation-status 必须为 draft 或 reviewed")
    if meta.get("discussion-id") != original.get("discussion-id"):
        raise ValueError(f"{translation}: 中英文 discussion-id 必须一致以共享讨论")
    anchors = lambda text: Counter(re.findall(r"\{#([^\s}]+)", text))
    if anchors(body) != anchors(translated_body):
        raise ValueError(f"{translation}: 中英文显式锚点不一致")
    if header_signatures(source_ast) != header_signatures(translated_ast):
        raise ValueError(f"{translation}: 中英文标题定位不一致；请保持标题层级和锚点 ID 相同，以便语言切换保留段落位置")
    if contribution_signatures(source_ast) != contribution_signatures(translated_ast):
        raise ValueError(f"{translation}: 中英文原作者、补充者或归属状态不一致")


def validate_sources(quarto):
    config = yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8"))
    giscus_settings(config)  # Reject incomplete service configuration before rendering.
    known = load_author_metadata()["guide-authors"]
    load_redirects()
    current = pages()
    asts = {}
    for root in language_roots():
        local_config = yaml.safe_load((root / "_quarto.yml").read_text(encoding="utf-8"))
        listed = list(chapters(local_config["book"]["chapters"]))
        actual = [str(p.relative_to(root)) for p in current if source_root(p) == root]
        if len(listed) != len(set(listed)) or set(listed) != set(actual):
            raise ValueError(f"{root}: 目录与正文不一致：未列入 {set(actual)-set(listed)}，缺失 {set(listed)-set(actual)}")
        discussion_ids = set()
        for path in (p for p in current if source_root(p) == root):
            if not path.is_file():
                raise ValueError(f"{path}: 缺少正文源文件")
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
            asts[path] = pandoc_json(quarto, path)
            validate_ast(asts[path]["blocks"], path, known)
    if len(language_roots()) > 1:
        chinese = {p.relative_to(BOOK).as_posix(): p for p in current if source_root(p) == BOOK}
        english = {p.relative_to(BOOK / "en").as_posix(): p for p in current if source_root(p) != BOOK}
        if set(chinese) != set(english):
            raise ValueError(f"中英文页面镜像不完整：缺少英文 {set(chinese)-set(english)}，缺少中文 {set(english)-set(chinese)}")
        for relative, source in chinese.items():
            validate_translation(source, english[relative], asts[source], asts[english[relative]])
    print(f"正文检查通过：{len(current)} 页，署名覆盖、作者名单、分语言目录与讨论标识有效。", flush=True)


def export_markdown(quarto):
    entries = {root: [] for root in language_roots()}
    records = {root: [] for root in language_roots()}
    for path in pages():
        root = source_root(path)
        meta, _ = frontmatter(path)
        relative = path.relative_to(root).with_suffix(".md")
        target = markdown_output(path)
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
        if root != BOOK and meta.get("translation-status") == "draft":
            text = "> English translation draft. Please check important details against the Chinese original.\n\n" + text
        target.write_text(text, encoding="utf-8")
        entries[root].append((str(relative), meta["title"]))
        # Index the expanded authored AST, not disclosure controls or site footers.
        plain = run([quarto, "pandoc", "--from=json", "--to=plain", "--wrap=none"],
                    input=json.dumps(ast), capture_output=True, text=True).stdout.strip()
        href = str(path.relative_to(root).with_suffix(".html"))
        records[root].append({"objectID": href, "href": href, "title": meta["title"],
                              "section": "", "text": plain})
    for root in language_roots():
        output = locale_output(root)
        if root == BOOK:
            index = ["# 西浦博士生非官方攻略", "", "与网页和 PDF 共用正文源。署名以普通文字保留；历史归属待确认不代表已经逐段核实。", "", "## 文章", ""]
        else:
            index = ["# Unofficial Guide for XJTLU PhD Students", "",
                     "English translations share the website and PDF sources. Draft translations require review. Original credits are retained; historical attribution may be unconfirmed.", "", "## Articles", ""]
        for relative, title in entries[root]:
            index.append(f"- [{title}](markdown/{relative})")
        (output / "llms.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
        (output / "search.json").write_text(json.dumps(records[root], ensure_ascii=False), encoding="utf-8")
    # GitHub Pages must copy leading-underscore Quarto assets without Jekyll.
    (OUTPUT / ".nojekyll").touch()
    print(f"纯 Markdown 导出完成：{sum(map(len, entries.values()))} 页，各语言独立索引。", flush=True)


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
        self.native_theme_ids = {}
        self.giscus_scripts = []
    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if fields.get("id"):
            identifier = fields["id"]
            # Quarto's pinned dual-theme output intentionally repeats these two
            # stylesheet IDs for light, dark, and fallback sheets. Restrict the
            # exception to its actual link markup; ordinary element IDs remain
            # unique even if they borrow one of the reserved stylesheet names.
            native_theme = (tag == "link" and "stylesheet" in fields.get("rel", "").split()
                            and identifier in {"quarto-bootstrap", "quarto-text-highlighting-styles"}
                            and bool({"quarto-color-scheme", "quarto-color-scheme-extra"}
                                     & set(fields.get("class", "").split())))
            if identifier in self.ids and not (native_theme and self.native_theme_ids.get(identifier)):
                self.duplicate_ids.add(identifier)
            self.native_theme_ids[identifier] = native_theme and self.native_theme_ids.get(identifier, True)
            self.ids.add(identifier)
        if tag in {"a", "img", "script", "link"}:
            for key in ("href", "src"):
                if fields.get(key):
                    self.urls.append(fields[key])
        if tag == "script" and (fields.get("src") == "https://giscus.app/client.js"
                                or fields.get("data-src") == "https://giscus.app/client.js"
                                or "guide-giscus-config" in fields.get("class", "").split()):
            self.giscus_scripts.append(fields)


def version_stylesheets():
    """Keep rendered pages paired with the current local reader stylesheet."""
    source = BOOK / "assets/guide.css"
    if not source.is_file():
        return 0  # Small fixture/legacy projects may not use the reader stylesheet.
    version = hashlib.sha1(source.read_bytes()).hexdigest()
    stylesheet = (OUTPUT / "assets/guide.css").resolve()

    class StylesheetLinks(HTMLParser):
        def __init__(self, text, document):
            super().__init__()
            self.document = document
            self.offsets = [0, *(match.end() for match in re.finditer("\n", text))]
            self.replacements = []
            self.feed(text)

        def handle_starttag(self, tag, attrs):
            fields = dict(attrs)
            if (tag != "link" or "stylesheet" not in (fields.get("rel") or "").lower().split()
                    or len([key for key, _ in attrs if key == "href"]) != 1):
                return
            href = fields.get("href") or ""
            try:
                parts = urlsplit(href)
            except ValueError:
                return
            if parts.scheme or parts.netloc or href.startswith("//"):
                return
            path = unquote(parts.path)
            target = OUTPUT / path.lstrip("/") if path.startswith("/") else self.document.parent / path
            if target.resolve() != stylesheet:
                return
            query = [part for part in parts.query.split("&") if unquote(part.split("=", 1)[0]) != "v"] if parts.query else []
            address = urlunsplit(("", "", parts.path, "&".join([*query, "v=" + version]), parts.fragment))
            if address == href:
                return
            raw = self.get_starttag_text()
            # Consume complete attributes so a quoted data/title value containing
            # the word href cannot be mistaken for the real href attribute.
            attributes = re.finditer(r'''([^\s"'<>/=]+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s"'=<>`]+))?''', raw)
            for attribute in attributes:
                if attribute[1].lower() == "href" and attribute[2] is not None:
                    line, column = self.getpos()
                    offset = self.offsets[line - 1] + column
                    self.replacements.append((offset + attribute.start(2), offset + attribute.end(2),
                                              '"' + escape(address, quote=True) + '"'))
                    break

    updated = 0
    for source in pages():
        document = OUTPUT / source.relative_to(BOOK).with_suffix(".html")
        if not document.is_file():
            continue
        text = document.read_text(encoding="utf-8")
        parser = StylesheetLinks(text, document)
        for start, end, replacement in reversed(parser.replacements):
            text = text[:start] + replacement + text[end:]
        if parser.replacements:
            document.write_text(text, encoding="utf-8")
            updated += 1
    if updated:
        print(f"网页样式版本已更新：{updated} 页。", flush=True)
    return updated


def validate_output(html_only):
    config = yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8"))
    giscus = giscus_settings(config)
    articles = {(OUTPUT / source.relative_to(BOOK).with_suffix(".html")).resolve() for source in pages()}
    redirects = redirect_outputs(".html")
    discussions = {
        (OUTPUT / source.relative_to(BOOK).with_suffix(".html")).resolve(): frontmatter(source)[0]["discussion-id"]
        for source in pages()
    } if giscus else {}
    english_articles = {(OUTPUT / source.relative_to(BOOK).with_suffix(".html")).resolve()
                        for source in pages() if source_root(source) != BOOK}
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
                script = parser.giscus_scripts[0]
                if "src" in script or "guide-giscus-config" not in script.get("class", "").split():
                    errors.add(f"{label} 的 Giscus 必须使用无 src、class 含 guide-giscus-config 的配置，由网页主题脚本加载")
                expected = {**giscus, "type": "application/json", "data-src": "https://giscus.app/client.js",
                            "data-term": discussions[path],
                            "data-lang": "en" if path in english_articles else "zh-CN"}
                for field, value in expected.items():
                    if script.get(field) != value:
                        errors.add(f"{label} 的 Giscus {field} 与配置或文章 discussion-id 不一致")
    if errors:
        raise ValueError("产物链接检查失败：\n" + "\n".join(sorted(errors)))
    for root in language_roots():
        output = locale_output(root)
        if not html_only and not (output / "xp-pgrs-unofficial-guide.pdf").exists():
            raise ValueError(f"{output}: 未生成整本 PDF")
        search = json.loads((output / "search.json").read_text(encoding="utf-8"))
        local_pages = [source for source in pages() if source_root(source) == root]
        expected_hrefs = {str(source.relative_to(root).with_suffix(".html")) for source in local_pages}
        if (len(search) != len(local_pages)
                or any("一起完善这一页" in entry["text"] or "Improve this page" in entry["text"] for entry in search)
                or (any("href" in entry for entry in search)
                    and {entry.get("href") for entry in search} != expected_hrefs)):
            raise ValueError(f"{output}: 搜索索引不完整、混入其他语言或供稿控件文本")
    print(f"产物检查通过：{len(articles)} 篇 HTML 文章、{len(redirects)} 个兼容跳转，本地链接和锚点有效。", flush=True)


def validate_markdown(quarto):
    articles = {markdown_output(source).resolve() for source in pages()}
    redirects = redirect_outputs(".md")
    documents = {}
    markdown_files = [path for root in language_roots() for path in (locale_output(root) / "markdown").rglob("*.md")]
    for path in markdown_files:
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


def validate_pdf(path=None):
    from pypdf import PdfReader
    path = path or OUTPUT / "xp-pgrs-unofficial-guide.pdf"
    reader = PdfReader(path)
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
    print(f"PDF 检查通过（{path.relative_to(OUTPUT)}）：{len(reader.pages)} 页，{internal} 个内部链接有效，附件使用在线绝对地址。", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-only", action="store_true", help="快速预览，仅生成网页与 Markdown")
    parser.add_argument("--check-only", action="store_true", help="只校验正文与署名，不渲染")
    args = parser.parse_args()
    quarto = os.environ.get("QUARTO") or shutil.which("quarto")
    if not quarto:
        raise ValueError("找不到 Quarto。请安装 1.10.19，或设置 QUARTO=/path/to/quarto。")
    giscus_settings(yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8")))
    prepare_english_config()
    validate_sources(quarto)
    if args.check_only:
        return
    # Clean generated output only; never edit the authored qmd or the LaTeX archive.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    run([quarto, "render", BOOK, "--to", "html" if args.html_only else "all"])
    if len(language_roots()) > 1:
        run([quarto, "render", BOOK / "en", "--to", "html" if args.html_only else "all"])
    version_stylesheets()
    export_markdown(quarto)
    export_redirects()
    validate_output(args.html_only)
    validate_markdown(quarto)
    if not args.html_only:
        for root in language_roots():
            validate_pdf(locale_output(root) / "xp-pgrs-unofficial-guide.pdf")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"构建失败：{exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(1)
