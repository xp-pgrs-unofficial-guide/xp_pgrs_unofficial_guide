# 维护者设置与发布

中文首页维护于 `book/index.qmd`，正文按主题维护于 `book/content/` 的六个子目录中；`book/en/` 保存逐篇对应的英文译文，作者页在两种语言各自的 `authors/` 下。运行 `python3 scripts/build.py` 一次，会构建两种语言的网站、整本 PDF 和纯 Markdown：中文在 `book/_book/`，英文在其 `en/` 子目录。Quarto 固定为 1.10.19；升级前先在分支完整构建并核对所有格式。

先阅读[项目数据流](data-flow.md)，可了解原始材料、临时中间数据、发布产物，以及评论与供稿进入正文的过程。[更新与维护流程](maintenance-workflow.md)用流程图区分人工操作与已自动化的检查、构建和发布步骤。

## 第一次启用 GitHub Pages

在仓库 **Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**。当前仓库为公开仓库，可使用 GitHub Free 的 Pages。部署环境 `github-pages` 如配置分支限制，应允许 `main`；保留既有审核要求。

`Build guide and deploy Pages` 在 `main` 有新推送时，先检查并构建全部格式，再部署网站；也可选择 `main` 手动运行。其他分支的推送、PR 和手动运行只验证并保存构建产物。网站地址为：

<https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/>

不要在 `book/_book/` 手工修正文；下次构建会覆盖它。部署前需要审核的是源文件 PR。

## 从 main 手动发布

在 Actions 中打开 **Build guide and deploy Pages**（`.github/workflows/CI.yml`），选择 **Run workflow → main → Run workflow**。也可使用 GitHub CLI：

```sh
gh workflow run CI.yml --ref main
```

部署会将 `main` 构建出来的网页、PDF 和 Markdown 发布到上面的 Pages 地址。日常修改先在工作分支提交 PR，审核并合并到 `main` 后自动发布。其他分支的构建产物可从 Actions 的 `guide-build` 附件下载；需要交互预览时可在本地运行 Quarto。

`book/_quarto.yml` 的 `book.repo-branch` 为 `main`，网站“提出修改（PR）”和查看源代码的链接都指向该分支；文章编辑链接与 Issue 草稿中的源分支使用同一配置。读者提交 PR 时应确认目标分支为 `main`。若未来调整发布分支，同时更新工作流、此配置、`CONTRIBUTING.md` 和中英文供稿说明。

“补充内容／纠错”使用 GitHub 支持的 `title`、`body` URL 参数，直接打开预填文章标题、链接、源文件、分支、`discussion-id` 和填写提示的 Issue 草稿。不要向该入口添加需要额外权限的标签、分派者等参数。直接新建 Issue 时，也可使用默认分支 `.github/ISSUE_TEMPLATE/` 中的投稿与纠错表单；修改表单需合并到 `main` 后生效。

## 配置文章评论

仓库已开启 Discussions，当前使用现有的 `Announcements` 公告分类保存文章评论。维护者设置如下：

1. 选择 Discussions 中的 **Announcements** 类型分类。本仓库使用 `Announcements`；也可另建“文章评论”公告分类，但切换分类时需要同步更新构建变量，并核对已有讨论的归属。
2. 安装 [giscus GitHub App](https://github.com/apps/giscus)，只授予本仓库访问权限。
3. 在 [giscus 配置页](https://giscus.app/zh-CN)选择本仓库和该分类，复制实际生成的仓库 ID、分类 ID。
4. 在 **Settings → Secrets and variables → Actions → Variables** 添加 `GISCUS_REPO_ID` 和 `GISCUS_CATEGORY_ID`。这两项是公开标识符，使用 repository variables 即可，无需新建访问令牌或 secrets。如果分类名称不是“文章评论”，另设 `GISCUS_CATEGORY` 为实际分类名称。
5. 在 Actions 中选择 **Run workflow → main** 手动部署，验证至少两篇文章下方出现对应语言的评论组件和 GitHub 登录入口，且不同文章关联不同讨论标识、同篇中英文共用标识。

当前配置的公开变量为：

| 变量 | 值 |
| --- | --- |
| `GISCUS_REPO_ID` | `R_kgDOH1Ttsw` |
| `GISCUS_CATEGORY_ID` | `DIC_kwDOH1Tts84CQ6ob` |
| `GISCUS_CATEGORY` | `Announcements` |

GitHub App 安装、Discussions 和 Actions variables 是仓库级设置，不属于某一个分支；正文和工作流通过 PR 合并到 `main` 后生效。新增 App 安装时可选择 **Only select repositories**，仅授权 `xp_pgrs_unofficial_guide`。变量已存在不代表 App 已安装，应在 [giscus 配置页](https://giscus.app/zh-CN)填写仓库全名确认可用。

未设置 Giscus 变量时，网页仍可阅读，文章显示通往 GitHub Discussions 的链接；不要用示例 ID 冒充已启用评论。若开始配置但两个 ID 不齐，构建会报错，避免静默发布失效的评论区。分支和 fork PR 的构建不依赖任何 secret，完全缺失评论配置也应通过构建。

评论按文章 frontmatter 的 `discussion-id` 关联，使用 giscus 的固定 term 和严格匹配。新文章必须分配唯一 ID，同篇英文译文使用相同 ID，改标题、移动文件时保留原 ID。不要为所有文章使用同一个 ID，也不要重命名已关联 Discussion 的匹配标识。删除内容时保留原讨论，便于追溯。

初次部署时没有对应 Discussion 属于正常情况；giscus 会在读者第一次留言或回应时自动建帖。严格匹配依赖正文中的 SHA-1 标识，让 giscus 自动创建即可，无需手工预建帖子或发布测试留言。评论区随当前网页明暗主题切换，界面语言与文章一致。构建会核对每篇文章实际生成的仓库、分类、固定标识、严格匹配、主题和语言设置，防止不同文章误用同一讨论。

本地测试评论可以临时在运行环境设置 `GISCUS_REPO_ID`、`GISCUS_CATEGORY_ID`（以及可选 `GISCUS_CATEGORY`）再构建。ID 不是密码，但不要把 GitHub 登录令牌写入网页、源文件或日志。

## 本地依赖与构建

安装 [Quarto 1.10.19](https://github.com/quarto-dev/quarto-cli/releases/tag/v1.10.19)、Python 3.12 和 `requirements-build.txt`。Ubuntu 的 PDF 依赖与 CI 一致：

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends texlive-xetex texlive-pictures texlive-lang-chinese texlive-latex-extra texlive-fonts-recommended texlive-plain-generic lmodern
python3 -m pip install -r requirements-build.txt
python3 scripts/build.py
```

PDF 使用 XeLaTeX 与 `ctexbook` 的 `fontset=fandol`，不依赖 macOS 系统字体。当前样式维护在 `book/pdf/`，参考历史 ElegantBook 的校园封面、深蓝横带、蓝色章节标题及页眉页脚，见[PDF 排版说明](../book/pdf/README.md)。构建使用当前发布资源副本，不读取 `archive/`；修改样式后需检查封面、目录、正文、表格和插图。

本机 Quarto 的 `pandoc` 包装进程异常时，可将 `PANDOC_BIN` 指向同版本 Quarto 附带的原生 Pandoc；它仅替代内容解析与导出调用，书籍渲染仍由 Quarto 完成。

HTML 预览可用 `python3 scripts/build.py --html-only`，只查源文件用 `--check-only`。运行一次构建后，用 `quarto preview book` 预览中文，`quarto preview book/en` 预览英文。

两种语言的产物分别包含 `xp-pgrs-unofficial-guide.pdf`、`markdown/content/<主题目录>/*.md`、作者页 Markdown、`llms.txt` 和 `search.json`。Quarto 1.10.19 的书籍项目尚不能依赖原生 `book.llms-txt`，当前通过构建导出 Markdown 和索引，每种语言都与网页、PDF 共用对应的 `.qmd` 正文。未来升级到包含书籍支持的稳定版后，再评估移除这一步；不要仅因配置 schema 接受该字段就认定已有产物。

## 双语、主题与作者页维护

`book/_quarto.yml` 维护共享目录及输出配置，`book/_languages.yml` 提供英文书名和主题目录译名。构建会生成 `book/en/_quarto.yml`，该文件已忽略，不手工编辑或提交。正文更新方法、译文来源哈希及 `draft`／`reviewed` 状态见[双语正文与翻译维护](../CONTRIBUTING.md#双语正文与翻译维护)。缺少对应译文、来源哈希过期或署名与锚点不一致都会导致构建失败。英文初稿在网页、Markdown 导出及 PDF 封面中提示待人工复核。

HTML 使用 Quarto 的 `light: cosmo`／`dark: darkly` 双主题，`respect-user-color-scheme` 让初次访问跟随系统；手动选择由浏览器保存并跨语言保留，Giscus 跟随当前主题。核验时至少检查系统默认、切换后的正文与署名卡片对比度、评论区，以及中英切换后主题和段落定位。

还应覆盖先切换主题再滚动到评论区，以及保存选择后刷新页面，确认延迟加载的评论也使用当前网页的配色。

作者中英文显示名集中在 `book/_authors.yml` 的 `guide-authors` 与 `guide-authors-en`，稳定 ID 相同。作者清单与主页在 `book/authors/` 和 `book/en/authors/`；`author-pages.lua` 从 `.contribution` 的原作者与补充者字段自动汇总参与文章。“归属待确认”是归属标记，不代表个人。网页只对连续且作者、补充者、确认状态相同的内容合并显示署名，源块和 PDF／Markdown 仍保留各块作者。

更改控件、署名或构建逻辑时，除完整构建外运行：

```sh
python3 -m unittest discover -s tests/attribution
python3 -m unittest discover -s tests/publishing
python3 -m unittest discover -s tests/build
node --test tests/ui/guide.test.js
```

## 调整文章目录与保留旧地址

六个主题文件夹与新增文章位置见[贡献说明](../CONTRIBUTING.md#文章目录与文件移动)。`book/index.qmd` 保留为首页；构建递归发现两种语言的各层文章与作者页，并校验各自的显式章节目录完整覆盖全部页面。章节目录决定网页与 PDF 的阅读顺序，文件系统排序只用于发现文件。

移动文章时同步移动对应译文，保留作者、补充者、文章 `discussion-id` 与已有锚点，更新章节目录、正文引用及 `book/redirects.yml` 中的别名目标。别名表中的旧 `.qmd` 路径应直接映射到当前文件；再次移动时同步改写所有历史别名目标，避免跳转链。

构建自动生成旧 HTML 地址的跳转页，保留 URL 查询参数和锚点；旧 Markdown 地址生成迁移提示并链接到当前文章。兼容页属于 `book/_book/` 生成结果，不在旧路径保留重复 `.qmd`。移动后运行源检查、HTML 预览和完整构建，核对当前地址、旧地址及图片附件链接。

## PDF Release

继续使用 `v*` 版本标签发布。先确认对应提交的完整构建成功，再推送版本标签。`Release PDF` 工作流检出该标签，重新测试并构建两种语言，将两份 PDF 同时上传到相应 GitHub Release；已有同名附件会更新。

| 语言 | 构建产物 | Release 附件名 |
| --- | --- | --- |
| 中文 | `book/_book/xp-pgrs-unofficial-guide.pdf` | `xp_pgrs_unofficial_guide_<去掉v的版本>.pdf` |
| 英文 | `book/_book/en/xp-pgrs-unofficial-guide.pdf` | `xp_pgrs_unofficial_guide_<去掉v的版本>_en.pdf` |

例如 `v1.1.0` 对应 `xp_pgrs_unofficial_guide_1.1.0.pdf` 和 `xp_pgrs_unofficial_guide_1.1.0_en.pdf`。中文版保留既有附件命名习惯，英文版通过 `_en` 区分。

网站首页和每篇文章页脚也提供两种语言的 PDF 入口：[中文版 PDF](https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/xp-pgrs-unofficial-guide.pdf)、[英文版 PDF](https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/en/xp-pgrs-unofficial-guide.pdf)。Pages 上的文件跟随 `main` 部署更新，Release 附件对应所选版本标签。

需要补发时，在 Actions 手动运行 `Release PDF`，输入已存在的 `v*` 标签；从标签运行时可省略输入。从分支手动运行且没有标签会明确失败，不会猜测版本或创建标签。历史 LaTeX 版本标签缺少新构建入口，保留其既有 Release，不用新工作流重发。

## 投稿审核与历史归档

维护者日常应关注 Issue、Discussions 和 PR 三个入口：Issue 收集投稿与纠错，Discussions 承载文章评论，PR 提供可直接审核的正文修改。采纳 Issue 或讨论中的建议后，需要整理为 `.qmd` 并通过 PR 合并到 `main`；这些建议不会自动同步成正文。

新作者可通过文章下方的预填 Issue 草稿提交普通文字。编辑核实署名和来源，在 `book/_authors.yml` 登记作者，将正文整理为署名块并通过 PR 审核；对代录内容保留投稿人的作者身份。稿件、评论与正式正文分开，避免未经核实的信息自动上线。

历史资料统一收在 `archive/`，目录与追溯方法见[历史归档说明](../archive/README.md)。`archive/latex/` 保留旧 LaTeX 源码、作者资料、图片、附件、模板和编辑器配置的原有相对目录。当前发布使用 `book/assets/` 中的资源，归档附件不会自动同步到正文。

`book/migration.json` 的 `legacy_root` 为 `archive/latex`，其中的原稿路径及文章 `legacy-source` 均相对该目录；核对时同时检查清单中的来源哈希。当前 Quarto 的文件路径仍相对 `book/`。`archive/tools/migrate_legacy.py` 仅保存一次性历史导入流程，会拒绝覆盖已有正文；日常发布继续运行 `python3 scripts/build.py`。

`archive/workflows/latex-to-pr.yml` 与 `archive/workflows/deploy-to-cloud.yml` 是历史参考副本，位于 `.github/workflows/` 之外，不会被 GitHub Actions 执行。旧转稿和云部署流程已停用；归档不操作既有云资源，如需清理旧云服务，由拥有者另行处理。
