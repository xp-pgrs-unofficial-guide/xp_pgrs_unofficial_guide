# 西浦博士生非官方攻略

🌐 [English version](README.en.md)

本攻略分享西浦博士生的学习、研究和生活经验，补充官方 induction 的实用信息。项目最初由西浦 PGR Society 发起，现由志愿编辑维护。

- [在线版](https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/)：可搜索、按文章阅读、讨论和提出修改；支持明暗主题及同篇中英切换。
- [PDF 下载](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/releases/latest)：保留离线阅读和版本归档。
- [投稿 / 纠错](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/issues/new)：使用 GitHub 账号提交文字，无需安装 Git 或 LaTeX；从文章下方进入可自动带上文章信息。

本仓库提供中文及[站内英文译文](https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/en/)，两种语言的同篇文章共享评论。英文初稿已标记为待人工复核。另有独立的[历史英文项目](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide_EN)，它不是本站中英切换的目标。

## 内容与贡献

中文首页 `book/index.qmd` 与 `book/content/` 下按六个主题目录组织的 `.qmd`（Quarto Markdown）是持续维护的中文正文，`book/en/` 保存同目录结构的英文译文。文件夹与主题的对应关系、新文章位置及旧地址兼容规则见[文章目录与文件移动](CONTRIBUTING.md#文章目录与文件移动)。每种语言的正文生成对应的网站、整本 PDF 和供 LLM 阅读的纯 Markdown。段落块显式记录作者和补充者；网页将连续相同署名合并显示，点击署名可进入作者主页，目录中的“作者与贡献者”汇总作者清单。代为整理、修正排版不会自动改变原作者。

网页首次访问跟随系统明暗主题，手动选择会在浏览器中保留，中英切换后继续使用；评论区同步切换主题。

可以通过文章下方的“补充内容／纠错”提交普通文字，Issue 草稿会预填文章信息；也可以点击“提出修改（PR）”，在 GitHub 网页中修改 Markdown。普通读者没有仓库写权限也可按提示 fork 后提交 Pull Request。评论和投稿均需 GitHub 登录，正文修改经过人工审核。详细步骤和段落署名示例见 [CONTRIBUTING.md](CONTRIBUTING.md)。

旧 LaTeX 原稿、作者资料和附件统一保存在 `archive/latex/`；旧工作流和一次性迁移工具也收在 `archive/`。这些历史资料供核对来源，日常修改写入 Quarto 正文。详见[历史归档说明](archive/README.md)。

正文、构建产物、网站和评论之间的关系见[项目数据流](docs/data-flow.md)，其中包含构建发布与读者互动的 Mermaid 图。

## 项目目录

| 位置 | 用途 |
| --- | --- |
| `book/` | 中文正文、作者表、共享配置和发布资源；`authors/` 保存作者页，`pdf/` 保存当前 PDF 样式。 |
| `book/en/` | 与中文逐篇对应的英文译文，配置由构建生成。 |
| `scripts/` | 当前构建入口 `build.py`。 |
| `tests/` | 署名、评论、供稿链接和文章路径的检查。 |
| `docs/` | 当前项目数据流与维护发布说明。 |
| `.github/` | 当前 CI、发布工作流和投稿模板。 |
| `archive/` | [历史 LaTeX、附件、旧工作流与迁移工具](archive/README.md)。 |

## 本地预览与构建

使用 Python 3.12、[Quarto 1.10.19](https://github.com/quarto-dev/quarto-cli/releases/tag/v1.10.19)，先安装 Python 依赖：

```sh
python3 -m pip install -r requirements-build.txt
python3 scripts/build.py --html-only
quarto preview book
```

完整构建还需 XeLaTeX、ctex 和 Fandol 中文字体（TeX 发行版自带）：

```sh
python3 scripts/build.py
```

一个构建命令会验证中英文对应关系和译文是否过期，并输出两种语言：中文在 `book/_book/`，英文在其 `en/` 子目录。每种语言均包含 `xp-pgrs-unofficial-guide.pdf`、`markdown/`、`llms.txt` 和搜索索引。PDF 的封面、章节与页眉页脚参考历史 ElegantBook 样式，由当前 Quarto 正文生成。只检查源文件可运行 `python3 scripts/build.py --check-only`。LLM 可直接阅读源文件或网站的 Markdown 导出，无需本项目专用 skill。

运行一次构建后，可用 `quarto preview book/en` 预览英文；不要手工修改生成的 `book/en/_quarto.yml`。

GitHub Actions 会验证分支推送和目标为 `main` 的 PR；`main` 的推送或手动运行会部署 Pages，其他分支仅构建并保存附件。正文修改通过 PR 合并到 `main` 后发布。`v*` 标签继续生成 GitHub Release PDF。Pages、评论及手动发布的方法见[维护者设置](docs/maintainer-setup.md)。
