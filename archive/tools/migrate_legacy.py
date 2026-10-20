#!/usr/bin/env python3
"""One-time, reviewable migration of the active legacy TeX book.

This is an import utility, not part of the publishing pipeline. The .qmd files
become the maintained source after import. This archived importer recreates the
initial flat content layout, not the current grouped book. Run only in an empty
book with --pandoc /path/to/pandoc.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY_ROOT = ROOT / "archive/latex"
CONTENT = ROOT / "book/content"
ASSETS = ROOT / "book/assets/imported"
PDFTOPPM = shutil.which("pdftoppm")
AUTHOR_NAMES = {"KW": ("吴开", "kaiwu.astro@gmail.com"), "Wu": ("Kai Wu", "kaiwu.astro@gmail.com"),
                "SZ": ("张世尧", "shiyao.zhang14@student.xjtlu.edu.cn"), "Shiyao": ("Shiyao", "shiyao.zhang14@student.xjtlu.edu.cn"),
                "Yue": ("Yue Zhou", "jasminezhou828@gmail.com")}
LABELS = {
    "chapter.author-ins": ("../contributing.qmd", "写作指南"),
    "necessary_resources": ("start-here.qmd#necessary_resources", "入口级网站和应用"),
    "must-do": ("compulsory-courses.qmd", "这些必须得做，不然毕不了业"),
    "fuli": ("other-benefits.qmd", "这些必须得看，不看吃大亏"),
    "sec.appendix": ("campus-map.qmd", "附录"),
    "section.how-research-works": ("how-research-works.qmd#section.how-research-works", "学术研究是怎么发生的"),
    "subsection.teamwork": ("how-research-works.qmd#subsection.teamwork", "团队合作"),
    "section.UoL_visit": ("liverpool-visit.qmd#section.UoL_visit", "利物浦访学"),
    "sec.mental_health": ("mental-health.qmd#sec.mental_health", "重视自己的负面情绪和抑郁倾向"),
    "sec.thesis_viva_graduation": ("thesis-and-graduation.qmd#sec.thesis_viva_graduation", "学位论文，论文答辩，和毕业"),
    "sec.official.flowchart": ("thesis-and-graduation.qmd#sec.official.flowchart", "官方流程和时间线"),
    "sec.graduation.time": ("thesis-and-graduation.qmd#sec.graduation.time", "每个步骤要等多久？如何预估时间？"),
    "sec.fund": ("conference-funding.qmd#sec.fund", "会议经费"),
    "sec.fuli_liverpool": ("liverpool-account.qmd#sec.fuli_liverpool", "利物浦账号自带福利"),
    "sec.IPAP": ("apr.qmd#sec.IPAP", "IPAP Interview 面试"),
    "sec.meeting_record": ("meeting-records.qmd#sec.meeting_record", "Liverpool Life 会议记录"),
    "sec.pc_backup": ("backup.qmd#sec.pc_backup", "电脑整机备份"),
    "sec.net_drive_backup": ("backup.qmd#sec.net_drive_backup", "网盘备份"),
}


def uncomment(text: str) -> str:
    """Remove TeX comments, retaining escaped percent signs and URL escapes."""
    out = []
    for line in text.splitlines():
        # Percent-encoded URL bytes are data here; the legacy file contains them
        # unescaped in \url commands, so preserve the complete URL line.
        if re.search(r"\\(?:url|href)\{[^}]*%[0-9A-Fa-f]{2}", line):
            out.append(line)
        else:
            out.append(re.split(r"(?<!\\)%", line, maxsplit=1)[0])
    return "\n".join(out).strip() + "\n"


def read(path: str) -> str:
    return uncomment((LEGACY_ROOT / path).read_text())


def active_sources(path="xp_pgrs_unofficial_guide.tex", seen=None):
    if seen is None:
        seen = []
    if path in seen:
        return seen
    seen.append(path)
    for target in re.findall(r"\\(?:include|input)\{([^}]+)\}", read(path)):
        target = target if target.endswith(".tex") else target + ".tex"
        if (LEGACY_ROOT / target).is_file():
            active_sources(target, seen)
    return seen


@dataclass
class Block:
    text: str
    authors: str = "unknown"
    unverified: bool = False


@dataclass
class Page:
    slug: str
    title: str
    sources: list[str]
    blocks: list[Block]
    group: str


def cut_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"\\section\{([^}]+)\}", text))
    return {m.group(1): text[m.start():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
            for i, m in enumerate(matches)}


def split_at(text: str, markers: list[str]) -> list[str]:
    positions = [0] + [text.index(marker) for marker in markers] + [len(text)]
    return [text[a:b] for a, b in zip(positions, positions[1:])]


def pages() -> list[Page]:
    result = []

    def add(slug, title, source, authors="unknown", group="其他攻略", unverified=False):
        result.append(Page(slug, title, [source], [Block(read(source), authors, unverified)], group))

    add("preface", "前言", "chapters/preface.tex", "kai-wu", "开始阅读")
    add("start-here", "Start here: 入口级网站和应用", "chapters/necessary_resources.tex", group="开始阅读")
    for slug, title, file in [
        ("compulsory-courses", "必修课程", "compulsory_lesson"),
        ("meeting-records", "Liverpool Life 会议记录", "meeting-record"),
        ("apr", "APR", "APR"),
        ("research-symposium", "Research Symposium", "symposium"),
    ]:
        add(slug, title, f"author-folder/Kai.Wu/{file}.tex", "kai-wu", "这些必须得做，不然毕不了业")
    for slug, title, file in [
        ("conference-funding", "会议经费", "fund"), ("stationery", "免费办公用品", "stationary"),
        ("printing", "免费打印", "print"), ("sports-vouchers", "体育馆代金券", "gym"),
        ("liverpool-account", "利物浦账号自带福利", "liverpool-account-fuli"),
    ]:
        add(slug, title, f"author-folder/Kai.Wu/{file}.tex", "kai-wu", "这些必须得看，不看吃大亏")
    result.append(Page("other-benefits", "其他福利", ["chapters/fuli.tex"],
                       [Block(cut_sections(read("chapters/fuli.tex"))["其他福利"])], "这些必须得看，不看吃大亏"))
    add("how-research-works", "学术研究是怎么发生的", "author-folder/Shiyao.Zhang14/how_research_works.tex", "shiyao-zhang", "最好要知道这些")
    ta = read("author-folder/Kai.Wu/TA.tex")
    parts = split_at(ta, [r"\subsection{如何成为一名TA}", r"\subsection{TA的工作种类，以及分别怎么做}",
                         r"\subsubsection{批作业}", r"\subsubsection{批改试卷}", r"\subsubsection{带Lab（实验课）}",
                         r"\subsubsection{如何做好讲Tutorial（习题课）}", r"\subsection{TA工资是多少，怎么结}"])
    ta_authors = ["kai-wu,yue-zhou", "yue-zhou", "unknown", "kai-wu", "unknown", "kai-wu", "yue-zhou", "unknown"]
    result.append(Page("teaching-assistant", "助教（Teaching Assistant）怎么做", ["author-folder/Kai.Wu/TA.tex"],
                       [Block(t, a, i == 0) for i, (t, a) in enumerate(zip(parts, ta_authors))], "最好要知道这些"))
    add("invigilation", "监考怎么做", "author-folder/Kai.Wu/invigilation.tex", "kai-wu,yue-zhou", "最好要知道这些", True)
    thesis = read("author-folder/Kai.Wu/thesis_viva_graduation.tex")
    before, after = thesis.split(r"\input{author-folder/Ziwen.Xie/viva.tex}")
    result.append(Page("thesis-and-graduation", "学位论文，论文答辩，和毕业",
                       ["author-folder/Kai.Wu/thesis_viva_graduation.tex", "author-folder/Ziwen.Xie/viva.tex"],
                       [Block(before, "kai-wu"), Block(read("author-folder/Ziwen.Xie/viva.tex"), "ziwen-xie"), Block(after, "kai-wu")], "最好要知道这些"))
    add("career", "和就业有关的重要信息", "author-folder/Kai.Wu/career.tex", "kai-wu", "最好要知道这些")
    add("backup", "大坑：假如明天你突然丢失电脑所有数据怎么办？——如何备份资料", "author-folder/Kai.Wu/backup.tex", "kai-wu")
    # Preserve the original chapter epigraph without attributing it to its first author.
    result[-1].blocks.insert(0, Block("——看一眼不亏，看两眼血赚\n"))
    result[-1].sources.insert(0, "chapters/others.tex")
    add("remote-access", "远程控制·如何校外访问校内电脑", "author-folder/Kai.Wu/remote-control.tex", "kai-wu")
    waist = read("author-folder/Yue.Zhou/waist.tex")
    waist_parts = split_at(waist, [r"\subsection{来自重度腰椎间盘突出、颈椎病患者的深度建议}"])
    result.append(Page("ergonomics", "我的老腰受不了了——如何保持颈椎、腰椎健康", ["author-folder/Yue.Zhou/waist.tex"],
                       [Block(waist_parts[0], "yue-zhou"), Block(waist_parts[1], "jialin-wang")], "其他攻略"))
    add("liverpool-visit", "利物浦访学", "author-folder/Shiyao.Zhang14/UoL_visit.tex", "shiyao-zhang,yue-zhou", "其他攻略", True)
    other = cut_sections(read("chapters/others.tex"))
    for slug, title, authors in [
        ("campus-vm", "西浦虚拟机", "unknown"), ("library-databases", "图书馆的文献数据库", "unknown"),
        ("suzhou-library", "苏州图书馆借书和免费送书", "unknown"),
        ("mental-health", "重视自己的负面情绪和抑郁倾向", "unknown"),
        ("recommended-software", "大家电脑上都装了什么软件？（期待你的补充）", "kai-wu"),
    ]:
        result.append(Page(slug, title, ["chapters/others.tex"], [Block(other[title], authors)], "其他攻略"))
    add("pitfalls", "避坑指南（待补）", "chapters/bikeng.tex", group="避坑指南")
    appendix = cut_sections(read("chapters/appendix.tex"))
    for slug, title, authors in [("campus-map", "校园地图", "unknown"), ("contacts", "学校电话", "unknown"),
                                ("join-us", "加入我们：评论机制及委员会化运作动议", "shiyao-zhang")]:
        result.append(Page(slug, title, ["chapters/appendix.tex"], [Block(appendix[title], authors)], "附录"))
    ack = read("chapters/acknowledgement.tex")
    ack_items = re.split(r"\\item\s*", ack)[1:]
    ack_items[-1] = ack_items[-1].split(r"\end{itemize}")[0]
    result.append(Page("acknowledgements", "致谢", ["chapters/acknowledgement.tex"],
                       [Block(r"\chapter{致谢}" + "\n" + ack_items[0]), Block(ack_items[1], "kai-wu"),
                        Block(ack_items[2], "shiyao-zhang"), Block(ack_items[3])], "附录"))
    add("changelog", "更新日志", "chapters/update_log.tex", "editorial", "附录")
    return result


def replace_command(text: str, name: str, fn) -> str:
    pattern = re.compile(r"\\" + re.escape(name) + r"\{")
    pos = 0
    while (m := pattern.search(text, pos)):
        depth, end = 1, m.end()
        while depth:
            if end >= len(text):
                raise ValueError(f"Unclosed {name}")
            if text[end] == "{" and text[end - 1] != "\\":
                depth += 1
            elif text[end] == "}" and text[end - 1] != "\\":
                depth -= 1
            end += 1
        replacement = fn(text[m.end():end - 1])
        text = text[:m.start()] + replacement + text[end:]
        pos = m.start() + len(replacement)
    return text


def preprocess(text: str, asset_manifest: dict, source_title: str) -> str:
    text = text.replace(r"校园地图：见附录 Chapter.\ref{sec.appendix}", r"校园地图：见附录 \href{campus-map.qmd}{校园地图}")
    text = text.replace(r"常用电话：见附录 Chapter.\ref{sec.appendix}", r"常用电话：见附录 \href{contacts.qmd}{学校电话}")
    text = text.replace(r"第 \ref{chapter.author-ins} 章 \space 写作指南", r"\ref{chapter.author-ins}")
    text = text.replace(r"\ref{section.how-research-works} 节 \space 学术研究是怎么发生的", r"\ref{section.how-research-works}")
    text = text.replace(r"\ref{section.UoL_visit} 节 \space 利物浦访学", r"\ref{section.UoL_visit}")
    text = text.replace(r"第 \ref{sec.mental_health} 章「重视自己的负面情绪和抑郁倾向」", r"\ref{sec.mental_health}")
    for macro, (name, email) in AUTHOR_NAMES.items():
        text = re.sub(r"\\" + macro + r"\b", lambda _: rf"\href{{mailto:{email}}}{{{name}}}", text)
    text = re.sub(r"\\(?:begin|end)\{newminipage\}(?:\[[^\]]*\])?", "\n", text)
    text = re.sub(r"\\begin\{minipage\}\{[^}]*\}", "\n", text)
    text = re.sub(r"\\end\{minipage\}", "\n", text)
    text = re.sub(r"\\(?:begin|end)\{(?:figure|table|flushright)\}(?:\[[^\]]*\])?", "\n", text)
    text = re.sub(r"\\begin\{subfigure\}\{[^}]*\}", "\n", text)
    text = text.replace(r"\end{subfigure}", "\n")
    # Tables used only for side-by-side pictures become a linear reading order.
    def picture_table(m):
        body = m.group(1)
        return re.sub(r"\\\\|&", "\n", body) if r"\includegraphics" in body else m.group(0)
    text = re.sub(r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}", picture_table, text, flags=re.S)
    text = replace_command(text, "caption", lambda value: "\n\\textit{" + value + "}\n")
    text = replace_command(text, "ref", lambda key: "\\href{" + LABELS[key][0] + "}{" + LABELS[key][1] + "}")
    text = replace_command(text, "email", lambda value: "\\href{mailto:" + value + "}{" + value + "}")
    text = re.sub(r"\\(?:clearpage|centering|hfill|kaishu)\b", "", text)
    text = re.sub(r"\\thispagestyle\{[^}]*\}", "", text)
    text = re.sub(r"\\vspace\{[^}]*\}", "\n", text)
    text = re.sub(r"\\emptyline(?:\{\})?", "\n", text)
    text = re.sub(r"\\LaTeX(?:\{\})?", "LaTeX", text)
    text = re.sub(r"\\space\b", " ", text)
    text = text.replace(r"\uline", r"\underline")
    text = re.sub(r"\\break\b", r"\\\\", text)
    # In the legacy source this section omitted the label referenced above.
    if source_title == "利物浦账号自带福利" and "sec.fuli_liverpool" not in text:
        text = text.replace(r"\section{利物浦账号自带福利}", r"\section{利物浦账号自带福利}\label{sec.fuli_liverpool}")

    def image(m):
        legacy = m.group(1)
        src = LEGACY_ROOT / legacy
        if not src.is_file():
            raise FileNotFoundError(src)
        author = src.parent.name if legacy.startswith("author-folder/") else "shared"
        dest = ASSETS / author / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        preview = dest
        if src.suffix.lower() == ".pdf":
            preview = dest.with_suffix(".png")
            if not preview.exists():
                if not PDFTOPPM:
                    raise RuntimeError("Install pdftoppm or provide --pdftoppm to import PDF previews")
                subprocess.run([str(PDFTOPPM), "-f", "1", "-singlefile", "-scale-to", "1800", "-png", str(src), str(preview.with_suffix(""))], check=True)
        new_path = "../assets/imported/" + author + "/" + preview.name
        asset_manifest[legacy] = {"source": legacy, "path": str(dest.relative_to(ROOT / "book")),
                                   "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                                   "preview": str(preview.relative_to(ROOT / "book"))}
        rendered = rf"\includegraphics{{{new_path}}}"
        if src.suffix.lower() == ".pdf":
            rendered += "\n\\par\\href{../assets/imported/" + author + "/" + dest.name + "}{下载原始 PDF}\n"
        return rendered

    text = re.sub(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", image, text)
    return text


def walk(value, fn):
    if isinstance(value, list):
        return [walk(x, fn) for x in value]
    if isinstance(value, dict):
        value = {k: walk(v, fn) for k, v in value.items()}
        return fn(value)
    return value


def convert(pandoc: str, text: str) -> tuple[str, list[dict]]:
    result = subprocess.run([pandoc, "-f", "latex", "-t", "json"], input=text, text=True, capture_output=True, check=True)
    doc = json.loads(result.stdout)
    raw = []

    def inspect(node):
        if node.get("t") in ("RawBlock", "RawInline"):
            raw.append(node)
        if node.get("t") == "Table":
            # Legacy p{60mm} and explicit cell newlines describe print layout,
            # rather than data. Ordinary cells keep this table portable to PDF.
            node = walk(node, lambda n: {"t": "Space"} if n.get("t") == "LineBreak" else n)
            node["c"][2] = [[alignment, {"t": "ColWidthDefault"}] for alignment, _ in node["c"][2]]
        if node.get("t") == "Image":
            # Descriptive filenames provide a useful fallback for legacy images.
            if not node["c"][1] or node["c"][1] == [{"t": "Str", "c": "image"}]:
                node["c"][1] = [{"t": "Str", "c": Path(node["c"][2][0]).stem.replace("_", " ")}]
        return node

    doc = walk(doc, inspect)
    if raw:
        raise ValueError("Unconverted raw LaTeX: " + json.dumps(raw, ensure_ascii=False))
    output = subprocess.run([pandoc, "-f", "json", "-t", "markdown+fenced_divs+bracketed_spans+pipe_tables-grid_tables-simple_tables-multiline_tables-smart", "--wrap=none"],
                            input=json.dumps(doc, ensure_ascii=False), text=True, capture_output=True, check=True)
    return output.stdout.strip(), doc["blocks"]


def main():
    global PDFTOPPM
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandoc", default=shutil.which("pandoc"), required=not shutil.which("pandoc"))
    parser.add_argument("--pdftoppm", default=PDFTOPPM, help="Poppler PDF-to-PNG executable; needed only for missing previews")
    args = parser.parse_args()
    if any((ROOT / "book").rglob("*.qmd")) or (ROOT / "book/migration.json").exists():
        parser.error("正文已存在。此脚本仅用于一次性历史导入；日常维护请修改 .qmd 并运行 scripts/build.py。")
    PDFTOPPM = args.pdftoppm
    CONTENT.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "purpose": "One-time import manifest; .qmd is now the maintained content source.",
                "legacy_root": "archive/latex", "legacy_entrypoint": "xp_pgrs_unofficial_guide.tex", "legacy_active_sources": active_sources(), "pages": [], "assets": [],
                "replaced": [{"source": "chapters/author-instruction.tex", "replacement": "contributing.qmd", "reason": "New web and Markdown contribution guide replaces the legacy TeX instructions."}],
                "excluded_inactive": ["chapters/non-xjtluer.tex", "chapters/pgrsociety.tex", "chapters/copyright.tex", "author-folder/Kai.Wu/train_ticket.tex", "author-folder/Kai.Wu/empty.tex", "author-guide/elegantbook-cn-example.tex", "author-guide/elegantbook-en-example.tex"],
                "notes": ["Chapter grouping headings are preserved in the book navigation.", "The other-advice chapter epigraph is retained in backup.qmd.",
                          "Existing facts, dates and recommendations are migrated without factual revision.", "Mixed-author legacy text is marked unverified rather than assigned by file directory."]}
    asset_manifest = {}
    page_specs = pages()
    discussion_ids = {p.slug + ".qmd": "xp-guide-" + p.slug for p in page_specs}
    discussion_ids["contributing.qmd"] = "xp-guide-contributing"
    for page in page_specs:
        pieces = []
        first_header_removed = False
        for block in page.blocks:
            prepared = preprocess(block.text, asset_manifest, page.title)
            markdown, _ = convert(args.pandoc, prepared)
            # Quarto creates the chapter heading from frontmatter. Preserve only
            # the old explicit anchor, avoiding a duplicate H1/empty PDF chapter.
            if not first_header_removed:
                m = re.search(r"^#+\s+(.+)$", markdown, flags=re.M)
                if m:
                    title_line = m.group(1)
                    top_id = re.search(r"\{#[^}]+\}", title_line)
                    page_anchor = ("::: " + top_id.group(0) + "\n:::\n\n") if top_id else ""
                    markdown = markdown[:m.start()] + markdown[m.end():]
                    first_header_removed = True
            if not markdown.strip():
                continue
            attrs = f'.contribution authors="{block.authors}"'
            if block.unverified or block.authors == "unknown":
                attrs += ' status="unverified"'
            pieces.append("::: {" + attrs + "}\n\n" + markdown.strip() + "\n\n:::")
        if not first_header_removed:
            page_anchor = ""
        # Pandoc's TeX section reader uses H1 for \section, H2 for \subsection.
        # The chapter-based pages already have the intended hierarchy.
        header = "---\n" + "title: " + json.dumps(page.title, ensure_ascii=False) + "\n"
        header += "discussion-id: xp-guide-" + page.slug + "\nlegacy-source:\n"
        header += "".join("  - " + src + "\n" for src in page.sources) + "---\n\n"
        canonical_anchor = "::: {#xp-guide-" + page.slug + "}\n:::\n\n"
        output = header + canonical_anchor + page_anchor + "\n\n".join(pieces) + "\n"
        if page.slug == "start-here":
            qr_table = """## 公众号

| 学校公众号 | 图书馆 | 学生服务（一站式） | IT |
|:--:|:--:|:--:|:--:|
| ![学校公众号二维码](../assets/imported/Kai.Wu/qrcode_XJTLU-China_1.jpg){width=110px} | ![图书馆二维码](../assets/imported/Kai.Wu/qrcode_XJTLU_library_1.jpg){width=110px} | ![学生服务二维码](../assets/imported/Kai.Wu/qrcode_student_service.jpg){width=110px} | ![IT二维码](../assets/imported/Kai.Wu/qrcode_IT.jpg){width=110px} |

"""
            output = re.sub(r"## 公众号\n.*?(?=另外，各学院)", lambda _: qr_table, output, flags=re.S)
        output = re.sub(r"\]\(([^)#]+\.qmd)\)",
                        lambda m: "](" + m[1] + "#" + discussion_ids[Path(m[1]).name] + ")", output)
        (CONTENT / (page.slug + ".qmd")).write_text(output)
        manifest["pages"].append({"path": "content/" + page.slug + ".qmd", "title": page.title,
                                  "group": page.group, "discussion_id": "xp-guide-" + page.slug,
                                  "sources": page.sources,
                                  "source_sha256": {p: hashlib.sha256((LEGACY_ROOT / p).read_bytes()).hexdigest() for p in page.sources}})
        print(page.slug)
    manifest["assets"] = list(asset_manifest.values())
    (ROOT / "book/migration.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
