# 参与编写攻略

欢迎分享亲身经历、补充有用资源和修正过期信息。首页在 `book/index.qmd`，其他正文写入 `book/content/` 对应主题目录的 `.qmd` 文件；历史 `.tex` 及相关资料统一放在 `archive/`，仅用于核对，见[历史归档说明](archive/README.md)。

## 提交文字投稿

推荐从目标文章下方点击“补充内容／纠错”：登录 GitHub 后，Issue 草稿会预填文章标题、网页链接、源文件、分支和文章标识，以及内容、署名和来源的填写提示。补充建议和资料后再提交即可，无需仓库写权限，也不需要安装 Git、学习 LaTeX 或配置构建环境。

也可直接[新建 Issue](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/issues/new)，手动填写目标文章链接或新文章主题。GitHub Issue Form 模板只从默认分支加载；当前预览分支使用不依赖模板的预填 Issue，在不合并 `main` 的情况下也可投稿。

编辑会核对来源和署名，把采用的内容整理成 Pull Request，经人工审核后发布。提交 Issue 或发表评论不会直接改动正文。Issue 和附件公开可见，请使用适合公开的资料；需要匿名时明确填写“匿名”。

## 在网页中提出修改

文章的“提出修改（PR）”会打开当前预览分支中的对应源文件。没有仓库写权限时，GitHub 会引导创建 fork；修改文字后选择提出更改，再创建 Pull Request，无需使用本地 Git。当前预览版本的 PR 目标分支（base）请选择 `codex/quarto-guide`，创建前检查文件差异，避免误将整套迁移内容提交给 `main`。拥有写权限的维护者也应创建修改分支，经 PR 审核后更新正文。

小改动可以直接修改原段落；新增经验通常单独建一个署名块。不要因代录、润色或排版调整删除原作者；对内容有实质补充时，在 `contributors` 中添加补充者。

## 文章目录与文件移动

`book/index.qmd` 保留为首页，其余文章放在 `book/content/` 下的六个主题目录中：

| 英文文件夹 | 中文目录主题 |
| --- | --- |
| `getting-started/` | 开始之前，含前言与常用网站、应用和资源 |
| `milestones/` | 毕业必经之路 |
| `resources/` | 资源与福利 |
| `research-work/` | 研究与工作 |
| `life-tools/` | 生活与工具 |
| `appendix/` | 附录与参与，含 `contributing.qmd` 供稿说明 |

新增文章应放入对应主题目录，例如 `book/content/milestones/`。网站和 PDF 的阅读顺序仍由 `book/_quarto.yml` 的章节目录显式决定；文件夹或文件名的排序不会改变导航顺序。构建会递归发现 `book/content/` 下的 `.qmd`，并检查首页及全部文章是否都被章节目录覆盖、是否有重复条目。

移动已有文章时，保留文章的 `discussion-id`、页首稳定锚点、段落锚点以及作者和补充者 ID。同步更新 `book/_quarto.yml`、正文中的相对引用和 `book/redirects.yml`。别名表记录“旧 `.qmd` 路径 → 当前 `.qmd` 路径”；历史别名应直接指向文件现在的位置，避免多次跳转。移动文件后也要核对图片和附件的相对路径。

构建根据别名表生成旧 HTML 地址的跳转页，保留访问时的查询参数和锚点；旧 Markdown 地址生成迁移提示并指向当前文章。这些是生成物，旧位置不保留第二份 `.qmd` 正文。按下文运行检查和预览后，再提交 PR。

## 段落署名与写作格式

作者登记在 `book/_authors.yml` 的 `guide-authors` 映射中，键为稳定 ID，值为公开显示名。首次投稿由编辑登记 ID；不要把邮箱、学号等非必要资料放入作者表。新内容必须填写真实作者或明确约定的匿名署名，不能使用历史内容的待确认作者占位值。

每个正文段落或紧密相关的列表、表格、图片使用 `.contribution` 块。`authors` 是原作者 ID；`contributors` 是后续实质补充者 ID；多人用英文逗号分隔。以下示例中的 ID 需替换为作者表里实际登记的 ID：

```markdown
::: {#p-your-topic-001 .contribution authors="your-author-id"}

这里写一段完整的经验。可以使用 **强调**、[链接](https://example.org/) 和普通 Markdown 列表。

:::

::: {#p-your-topic-002 .contribution authors="original-author-id" contributors="your-author-id"}

这里是保留原作者署名、经过另一位作者实质补充的段落。

:::
```

块 ID（示例中的 `#p-your-topic-001`）可选，需要为某段提供稳定引用时再添加；文章评论使用文章自身的 `discussion-id`。使用块 ID 时需在全书中唯一，修改内容、移动段落时保留原 ID。拆分已带 ID 的段落时，为新增锚点分配新 ID，并保留相应作者。不要用自动编号或当前行号生成 ID。

历史迁移中无法确定作者的段落会明确标记 `status="unverified"`，表示署名待核实；提供证据后由编辑更新作者并移除该标记。不要依据最后一次 Git 提交者直接推断原作者。

新文章应在对应主题目录中复制附近文章的 frontmatter，设置标题、唯一且长期保留的 `discussion-id`（格式 `xp-guide-主题英文名`），并加入 `book/_quarto.yml` 的章节目录。页首保留与 `discussion-id` 同名的空 Div，作为文章的稳定链接锚点；复制新文章时一起修改。文章标题由 frontmatter 自动生成，正文从二级标题 `##` 开始，不再重复写一级标题。改文章标题或文件路径时保留 `discussion-id` 和页首锚点，以便继续使用原有讨论。

正文使用普通 Markdown；图片放入 `book/assets/`，使用相对于文章的路径引用并填写简短说明。引用本书其他内容时使用 `[标题](文件.qmd#稳定锚点)`，确保网页、PDF 与 Markdown 都能跳转，并在预览中核对。

## 本地检查与预览

Python 3.12 与 Quarto 1.10.19：

```sh
python3 -m pip install -r requirements-build.txt
python3 scripts/build.py --check-only
python3 scripts/build.py --html-only
quarto preview book
```

完整构建还需要包含 ctex、Fandol 字体的 XeLaTeX 环境：

```sh
python3 scripts/build.py
```

Pull Request 请说明改动主题、资料来源及作者归属。CI 会验证源文件并构建网页、PDF 和纯 Markdown，输出可从 Actions 的 `guide-build` artifact 下载。不要把 `book/_book/` 或缓存文件提交到仓库。
