# 参与编写攻略

欢迎分享亲身经历、补充有用资源和修正过期信息。中文首页在 `book/index.qmd`，其他正文写入 `book/content/` 对应主题目录的 `.qmd` 文件，英文对应文件在 `book/en/`；历史 `.tex` 及相关资料统一放在 `archive/`，仅用于核对，见[历史归档说明](archive/README.md)。

## 提交文字投稿

推荐从目标文章下方点击“补充内容／纠错”：登录 GitHub 后，Issue 草稿会预填文章标题、网页链接、源文件、分支和文章标识，以及内容、署名和来源的填写提示。补充建议和资料后再提交即可，无需仓库写权限，也不需要安装 Git、学习 LaTeX 或配置构建环境。

也可直接[新建 Issue](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/issues/new/choose)，选择投稿或纠错表单，填写目标文章链接或新文章主题。文章下方的入口直接打开预填 Issue 草稿，方便保留页面信息。

编辑会核对来源和署名，把采用的内容整理成 Pull Request，经人工审核后发布。提交 Issue 或发表评论不会直接改动正文。Issue 和附件公开可见，请使用适合公开的资料；需要匿名时明确填写“匿名”。

## 在网页中提出修改

文章的“提出修改（PR）”会打开 `main` 中的对应源文件。没有仓库写权限时，GitHub 会引导创建 fork；修改文字后选择提出更改，再创建 Pull Request，无需使用本地 Git。PR 的目标分支（base）请选择 `main`，创建前检查文件差异。拥有写权限的维护者也应创建修改分支，经 PR 审核并合并到 `main` 后发布正文。

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

新增文章应放入对应主题目录，例如 `book/content/milestones/`。网站和 PDF 的阅读顺序仍由 `book/_quarto.yml` 的章节目录显式决定；文件夹或文件名的排序不会改变导航顺序。构建会递归发现正文和 `book/authors/` 下的 `.qmd`，检查每种语言的首页、文章和作者页是否被章节目录完整覆盖、是否有重复条目。英文目录从共享配置生成。

移动已有文章时，同步移动 `book/en/` 中的对应译文，保留文章的 `discussion-id`、页首稳定锚点、段落锚点以及作者和补充者 ID。同步更新 `book/_quarto.yml`、正文中的相对引用和 `book/redirects.yml`。别名表记录“旧 `.qmd` 路径 → 当前 `.qmd` 路径”；历史别名应直接指向文件现在的位置，避免多次跳转。移动文件后也要核对图片和附件的相对路径。

构建根据别名表生成旧 HTML 地址的跳转页，保留访问时的查询参数和锚点；旧 Markdown 地址生成迁移提示并指向当前文章。这些是生成物，旧位置不保留第二份 `.qmd` 正文。按下文运行检查和预览后，再提交 PR。

## 双语正文与翻译维护

中英文文章按相同相对路径对应，例如 `book/content/milestones/apr.qmd` 与 `book/en/content/milestones/apr.qmd`。两边使用相同的 `discussion-id`、显式锚点和署名块，网页切换语言后仍对应同一篇文章与讨论。译文需完整保留原内容的条件、日期、链接和作者，不因翻译改写历史事实。

英文 frontmatter 除标题、讨论标识和历史来源外，还包含：

```yaml
lang: en
translation-source: content/milestones/apr.qmd
translation-source-sha256: 中文源文件原始字节的SHA256
translation-status: draft
```

`draft` 表示英文初稿待人工复核，`reviewed` 表示已复核。中文修改后，先核对差异并同步译文，再更新来源哈希；已复核译文发生实质变化时，先改回 `draft`，复核后再恢复。构建会拒绝缺少对应页面、来源哈希过期、署名或显式锚点不一致的译文。不能只更新哈希来掩盖未翻译的修改。计算来源哈希可用：

```sh
python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('book/content/milestones/apr.qmd').read_bytes()).hexdigest())"
```

本地图片仍共用 `book/assets/`；英文文件引用时须按自身位置调整相对路径。标题层级和段落应与中文对应；为两边的小节标题显式填写相同的 `{#稳定标识}`，构建会检查标题定位一致。新增文章需同时补充对应译文；若需帮助，可先提交 Issue，由编辑协助整理。

共享目录和输出设置维护于 `book/_quarto.yml`，英文书名和目录主题译名维护于 `book/_languages.yml`。`book/en/_quarto.yml` 是构建生成物，不手工编辑或提交。

## 段落署名与写作格式

作者登记在 `book/_authors.yml`，`guide-authors` 和 `guide-authors-en` 分别提供中英文公开显示名，两者使用相同的稳定 ID。首次投稿由编辑登记 ID；不要把邮箱、学号等非必要资料放入作者表。新内容必须填写真实作者或明确约定的匿名署名，不能使用历史内容的待确认作者占位值。

正文按实际作者划分为相邻的 `.contribution` 块。一个块可以包含同一作者连续撰写的多段文字、标题、列表、表格和图片；作者变化时，先关闭当前块，再另起一块。不要嵌套署名块。网页会将连续且原作者、补充者、确认状态均一致的内容只显示一次署名，遇到变化重新显示；源文件仍需逐块标记，PDF 与 Markdown 继续保留各块署名。不要为了网页去重而删掉源署名。

以下用已登记的两个作者 ID 演示相邻署名块。示例中的文字和 ID 应按实际内容及作者替换：

```markdown
::: {#p-your-topic-001 .contribution authors="shiyao-zhang"}

这里写经确认由张世尧提供的内容。

同一作者接着写的下一段也可以放在这个块里。

:::

::: {#p-your-topic-002 .contribution authors="yue-zhou"}

这里写经确认由 Yue Zhou 提供的内容。

:::
```

`authors` 是原作者 ID；`contributors` 是后续实质补充者 ID；多人用英文逗号分隔。按内容实际形成的过程选择：

| 内容情况 | 块上的署名属性 |
| --- | --- |
| 某段由张世尧撰写 | `authors="shiyao-zhang"` |
| 某段由 Yue Zhou 撰写 | `authors="yue-zhou"` |
| 同一段确实由两人共同撰写 | `authors="shiyao-zhang,yue-zhou"` |
| 保留张世尧原文，Yue Zhou 做了实质补充 | `authors="shiyao-zhang" contributors="yue-zhou"` |

若补充者提供的是可以独立成段的新内容，可以另建属于补充者的块。录入、排版或改错字不构成实质补充，不因此改变署名。示例 ID 应替换为实际作者在作者表中登记的 ID。

块 ID（示例中的 `#p-your-topic-001`）可选，需要为某段提供稳定引用时再添加；文章评论使用文章自身的 `discussion-id`。使用块 ID 时需在全书中唯一，修改内容、移动段落时保留原 ID。拆分已带 ID 的段落时，为新增锚点分配新 ID，并保留相应作者。不要用自动编号或当前行号生成 ID。

历史迁移中无法确定具体段落归属时保留 `status="unverified"`；连作者身份也无法确认时使用历史占位值 `authors="unknown" status="unverified"`。提供证据后由编辑更新作者，并在归属确认后移除待核实标记。不要依据最后一次 Git 提交者直接推断原作者。

新文章应在对应主题目录中复制附近文章的 frontmatter，设置标题、唯一且长期保留的 `discussion-id`（格式 `xp-guide-主题英文名`），并加入 `book/_quarto.yml` 的章节目录。页首保留与 `discussion-id` 同名的空 Div，作为文章的稳定链接锚点；复制新文章时一起修改。文章标题由 frontmatter 自动生成，正文从二级标题 `##` 开始，不再重复写一级标题。改文章标题或文件路径时保留 `discussion-id` 和页首锚点，以便继续使用原有讨论。

正文使用普通 Markdown；图片放入 `book/assets/`，使用相对于文章的路径引用并填写简短说明。引用本书其他内容时使用 `[标题](文件.qmd#稳定锚点)`，确保网页、PDF 与 Markdown 都能跳转，并在预览中核对。

## 作者清单与主页

目录中的作者清单和每位作者的主页位于 `book/authors/`，英文页位于 `book/en/authors/`。主页依据现有 `.contribution` 的 `authors` 与 `contributors` 自动汇总参与文章，不根据 Git 提交者推断作者，也不推断个人简介。“归属待确认”是历史材料的归属标记，不代表某位作者。

登记新作者时，在作者表补充两种语言的显示名，并参照已有作者页添加中英文页面及共享章节目录条目。作者页的 `.guide-author-profile` 占位 Div 中填写对应的 `data-guide-author-id`；它必须放在署名内容块内，使网页、Markdown 和整本 PDF 都能原位生成列表。参与文章清单由构建汇总，无需手工重复维护。公开简介或外部主页仅在本人提供或确认后填写。

## 本地检查与预览

Python 3.12 与 Quarto 1.10.19：

```sh
python3 -m pip install -r requirements-build.txt
python3 scripts/build.py --check-only
python3 scripts/build.py --html-only
quarto preview book
```

运行构建后，也可用 `quarto preview book/en` 预览英文。完整构建同时生成两种语言的 PDF、Markdown 和检索索引，还需要包含 ctex、Fandol 字体的 XeLaTeX 环境：

```sh
python3 scripts/build.py
```

针对署名、控件或构建逻辑的修改，可运行以下测试：

```sh
python3 -m unittest discover -s tests/attribution
python3 -m unittest discover -s tests/publishing
python3 -m unittest discover -s tests/build
node --test tests/ui/guide.test.js
```

预览时核对系统默认主题、手动切换、同篇语言切换、作者链接，以及连续署名的显示。PDF 样式修改需完整构建并检查封面、目录和正文页。

Pull Request 请说明改动主题、资料来源及作者归属。CI 会验证源文件并构建网页、PDF 和纯 Markdown，输出可从 Actions 的 `guide-build` artifact 下载。不要把 `book/_book/` 或缓存文件提交到仓库。
