"""Validate short bilingual update records and resolve their stable article IDs.

The source records are deliberately independent of Git history and generated
pages.  The build passes its current source inventory and frontmatter reader so
the same resolver works for the website, PDF, and Markdown exports.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
import re

import yaml


GENERATED_NAME = "_updates.generated.yml"
LOCALES = ("zh-CN", "en")
IDENTIFIER = re.compile(r"xp-guide-[a-z0-9]+(?:-[a-z0-9]+)*")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class UpdateLoader(yaml.SafeLoader):
    """Reject duplicate fields instead of silently losing an editor's text."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("更新记录的字段名必须是字符串")
            if key in seen:
                raise ValueError(f"更新记录包含重复字段：{key}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _summary(value, label):
    if (not isinstance(value, str) or not value.strip() or value != value.strip()
            or any(character in value for character in "\r\n")):
        raise ValueError(f"{label} 必须是非空、单行的一句话摘要")
    return value


def _load_record(path):
    try:
        record = yaml.load(path.read_text(encoding="utf-8"), Loader=UpdateLoader)
    except (yaml.YAMLError, ValueError) as exc:
        raise ValueError(f"{path}: 更新记录不是合法 YAML：{exc}") from exc
    required = {"date", "type", "summary", "articles"}
    if not isinstance(record, dict) or set(record) != required:
        raise ValueError(f"{path}: 更新记录必须且只能包含 date、type、summary、articles 字段")
    raw_date = record["date"]
    # SafeLoader may already have converted an unquoted ISO date to date.
    # datetime (a date subclass), numbers, and timestamps are not event dates.
    value = raw_date.isoformat() if type(raw_date) is date else raw_date
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError(f"{path}: date 必须是 YYYY-MM-DD 日期")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{path}: date 不是有效日期：{value}") from exc
    kind = record["type"]
    if kind not in ("content", "site"):
        raise ValueError(f"{path}: type 必须是 content 或 site")
    summaries = record["summary"]
    if not isinstance(summaries, dict) or set(summaries) != set(LOCALES):
        raise ValueError(f"{path}: summary 必须且只能提供 zh-CN、en 两种摘要")
    summaries = {locale: _summary(summaries[locale], f"{path}: summary.{locale}") for locale in LOCALES}
    articles = record["articles"]
    if (not isinstance(articles, list)
            or any(not isinstance(item, str) or not IDENTIFIER.fullmatch(item) for item in articles)):
        raise ValueError(f"{path}: articles 必须是 xp-guide-* 稳定文章标识列表")
    if len(articles) != len(set(articles)):
        raise ValueError(f"{path}: articles 包含重复文章标识")
    if kind == "content" and not articles:
        raise ValueError(f"{path}: 内容更新必须关联至少一篇文章")
    return {"id": path.stem, "date": value, "type": kind, "summary": summaries, "articles": articles}


def _source_identifiers(body):
    """Read explicit stable anchors, excluding fenced examples of source markup."""
    lines = []
    fence = None
    for line in body.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
            continue
        if fence is None:
            # Inline code can also contain literal examples of anchor syntax.
            lines.append(re.sub(r"(`+).*?\1", "", line))
    return Counter(re.findall(r"\{#(xp-guide-[a-z0-9-]+)(?=[\s}])", "\n".join(lines)))


def _article_index(book, sources, read_source):
    result = {locale: {} for locale in LOCALES}
    for source in sources:
        if not source.is_file():
            raise ValueError(f"{source}: 缺少正文源文件")
        english = source.is_relative_to(book / "en")
        root, locale = (book / "en", "en") if english else (book, "zh-CN")
        meta, body = read_source(source)
        identifier = meta.get("discussion-id", "")
        title = meta.get("title")
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            raise ValueError(f"{source}: 更新记录无法使用缺失或不合法的 discussion-id")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{source}: 缺少文章标题")
        anchors = _source_identifiers(body)
        if anchors[identifier] != 1:
            raise ValueError(f"{source}: 稳定文章标识 {identifier} 必须有且只有一个显式页首锚点")
        for anchor, count in anchors.items():
            if count != 1 or anchor in result[locale]:
                raise ValueError(f"{source}: 文章标识 {anchor} 重复或存在歧义（{locale}）")
            result[locale][anchor] = {"path": source.relative_to(root).as_posix(), "title": title.strip()}
    return result


def load_updates(book: Path, sources, read_source):
    """Return normalized records, with links to the current bilingual articles."""
    directory = book / "updates"
    if not directory.exists():
        return []  # Older single-language fixtures need no update record tree.
    paths = sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])
    records, slugs = [], set()
    for path in paths:
        if not path.is_file() or not SLUG.fullmatch(path.stem):
            raise ValueError(f"{path}: 更新记录文件名必须是小写字母、数字和连字符组成的稳定标识")
        if path.stem in slugs:
            raise ValueError(f"{path}: 更新记录文件标识重复：{path.stem}")
        slugs.add(path.stem)
        records.append(_load_record(path))
    if any(record["articles"] for record in records):
        articles = _article_index(book, sources, read_source)
        for record in records:
            resolved = []
            for identifier in record["articles"]:
                localized = {}
                for locale in LOCALES:
                    if identifier not in articles[locale]:
                        raise ValueError(f"更新记录 {record['id']}: 无法定位文章标识 {identifier}（{locale}）")
                    localized[locale] = articles[locale][identifier]
                if localized["zh-CN"]["path"] != localized["en"]["path"]:
                    raise ValueError(f"更新记录 {record['id']}: 文章标识 {identifier} 的中英文承接路径不一致")
                resolved.append({"path": localized["zh-CN"]["path"], "anchor": identifier,
                                 "title": {locale: localized[locale]["title"] for locale in LOCALES}})
            record["articles"] = resolved
    return sorted(records, key=lambda record: (-date.fromisoformat(record["date"]).toordinal(), record["id"]))
