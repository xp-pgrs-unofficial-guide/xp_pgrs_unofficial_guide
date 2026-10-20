# 历史资料归档

这里保存 Quarto 迁移之前的 LaTeX 原稿与相关材料，供核对原文、署名和迁移来源。资料保留其历史状态，不会自动更新；新的正文、图片和附件维护于 [`book/`](../book/)，日常构建入口为 [`scripts/build.py`](../scripts/build.py)。

| 位置 | 保存内容 |
| --- | --- |
| [`latex/`](latex/) | 旧 LaTeX 项目的完整目录：主 `.tex`、`chapters/`、`author-folder/`、`author-guide/`、`figure/`、`fileshare/`、`elegantbook.cls`、`.vscode/` 和 `seafile-ignore.txt`。 |
| [`workflows/`](workflows/) | 旧 LaTeX 转稿与云部署工作流的参考副本。它们位于 `.github/workflows/` 之外，不会被 GitHub Actions 执行。 |
| [`tools/migrate_legacy.py`](tools/migrate_legacy.py) | 一次性历史导入工具，用于理解最初的 LaTeX 到 Markdown 迁移过程。 |

## 核对旧原稿

需要查看旧文章或附件时，以 `archive/latex/` 作为旧项目根目录打开，入口为 [`xp_pgrs_unofficial_guide.tex`](latex/xp_pgrs_unofficial_guide.tex)。该目录内保留原来的相对结构，章节引用、作者资料与附件位置可按原稿核对。旧 `.vscode/` 配置也随项目归档，不再作为当前仓库的编辑器配置。

[`book/migration.json`](../book/migration.json) 的 `legacy_root` 指向仓库内的 `archive/latex`。清单中的 `legacy_entrypoint`、`legacy_active_sources`、`sources`、`source_sha256` 的键、附件的 `source`、`replaced` 的 `source` 和 `excluded_inactive`，以及 Quarto frontmatter 的 `legacy-source`，均相对这个目录。原来的相对路径和来源哈希保留，例如 `chapters/preface.tex` 对应本仓库的 `archive/latex/chapters/preface.tex`。

清单中当前正文、附件的 `path` 与 `replacement` 相对 `book/`；`import_path` 和 `import_replacement` 记录最初导入时的输出位置。归档移动不会改变文章的作者、段落锚点或评论标识。

## 日常维护入口

当前网页、PDF 和 Markdown 使用 `book/` 中的 Quarto 正文与资源。`book/assets/imported/` 是当前发布需要的资源副本；这里的历史附件用于追溯，两者不会自动同步。补充或纠错请按[贡献说明](../CONTRIBUTING.md)修改当前正文。

历史导入工具不是当前 Quarto 文档的再生成器：它保留最初导入时的文章划分和输出方式，并会拒绝覆盖已经存在的 `.qmd` 正文。日常预览和发布使用 `python3 scripts/build.py`，详见[维护者说明](../docs/maintainer-setup.md)。
