# 西浦博士生非官方攻略

🌐 [English version](README.en.md)

本攻略分享西浦博士生的学习、研究和生活经验，补充官方 induction 的实用信息。项目最初由西浦 PGR Society 发起，现由志愿编辑维护。

- [在线版](https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/)：可搜索、按文章阅读、讨论和提出修改；首次上线需维护者启用 GitHub Pages。
- [PDF 下载](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/releases/latest)：保留离线阅读和版本归档。
- [投稿 / 纠错](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/issues/new/choose)：使用 GitHub 账号填写表单，无需安装 Git 或 LaTeX。

本仓库维护中文内容；另有独立的[英文版项目](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide_EN)。

## 内容与贡献

`book/content/` 中的 `.qmd`（Quarto Markdown）是持续更新的唯一正文来源。同一份内容生成网站、整本 PDF 和供 LLM 阅读的纯 Markdown。段落块显式记录作者和补充者，代为整理、修正排版不会自动改变原作者。

可以通过投稿表单提交普通文字，由编辑审核后纳入；也可以点击网站的编辑链接，在 GitHub 网页中修改 Markdown 并提交 Pull Request。评论和投稿均需 GitHub 登录，正文修改经过人工审核。详细步骤和段落署名示例见 [CONTRIBUTING.md](CONTRIBUTING.md)。

根目录的 LaTeX 入口、`chapters/` 和 `author-folder/` 保留为历史快照，便于核对原文，不再接收新正文。旧 LaTeX 转稿与云部署工作流已归档到 `docs/legacy-workflows/`，不会再自动生成第二份正文。

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

构建会先验证内容，输出到 `book/_book/`。整本 PDF 为 `xp-pgrs-unofficial-guide.pdf`；纯 Markdown 位于 `markdown/content/`，索引为 `llms.txt`。只检查源文件可运行 `python3 scripts/build.py --check-only`。LLM 可直接阅读源文件或网站的 Markdown 导出，无需本项目专用 skill。

GitHub Actions 会验证分支和 PR；`main` 的推送或手动运行会部署 Pages，`codex/quarto-guide` 也可手动部署以预览，普通分支推送不部署。`v*` 标签继续生成 GitHub Release PDF。首次配置 Pages、评论及分支预览的方法见[维护者设置](docs/maintainer-setup.md)。
