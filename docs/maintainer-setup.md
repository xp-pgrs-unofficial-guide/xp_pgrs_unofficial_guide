# 维护者设置与发布

正文的唯一维护入口是 `book/content/`。网站、整本 PDF、纯 Markdown 均由 `python3 scripts/build.py` 生成到 `book/_book/`。Quarto 固定为 1.10.19；升级前先在分支完整构建并核对所有格式。

## 第一次启用 GitHub Pages

在仓库 **Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**。当前仓库为公开仓库，可使用 GitHub Free 的 Pages。部署环境 `github-pages` 如配置分支限制，应允许 `main` 和用于手动预览的 `codex/quarto-guide`；保留既有审核要求。

合并到 `main` 后，`Build guide and deploy Pages` 会先检查并构建全部格式，再部署网站。也可选择 `main` 手动运行。`codex/quarto-guide` 只在手动触发时部署；该分支的普通推送、PR 和其他分支的运行只验证和保存构建产物。网站地址为：

<https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/>

不要在 `book/_book/` 手工修正文；下次构建会覆盖它。部署前需要审核的是源文件 PR。

## 不合并 main，手动预览当前分支

先推送 `codex/quarto-guide`，再在 Actions 中打开 `.github/workflows/CI.yml` 对应工作流，选择 **Run workflow → codex/quarto-guide → Run workflow**。工作流列表的显示名可能仍是默认分支里的旧名称 `test-compile`，以文件路径为准。也可使用 GitHub CLI：

```sh
gh workflow run CI.yml --ref codex/quarto-guide
```

部署会发布当前分支构建出来的网页、PDF 和 Markdown，不会合并或修改 `main`。它使用上面的同一个 Pages 地址，不是独立的分支预览网址；以后从 `main` 部署会更新这个网站。普通推送当前分支不会更新网站，需要再次手动运行。

当前分支尚未合并时，网站中的编辑链接和 Issue 表单仍按正式版本的 `main` 路径配置；正文浏览、搜索、署名和下载可用于预览，贡献入口在正式合并后生效。

## 配置文章评论

仓库已开启 Discussions，当前使用现有的 `Announcements` 公告分类保存文章评论。维护者设置如下：

1. 选择 Discussions 中的 **Announcements** 类型分类。本仓库使用 `Announcements`；也可另建“文章评论”公告分类，但切换分类时需要同步更新构建变量，并核对已有讨论的归属。
2. 安装 [giscus GitHub App](https://github.com/apps/giscus)，只授予本仓库访问权限。
3. 在 [giscus 配置页](https://giscus.app/zh-CN)选择本仓库和该分类，复制实际生成的仓库 ID、分类 ID。
4. 在 **Settings → Secrets and variables → Actions → Variables** 添加 `GISCUS_REPO_ID` 和 `GISCUS_CATEGORY_ID`。这两项是公开标识符，使用 repository variables 即可，无需新建访问令牌或 secrets。如果分类名称不是“文章评论”，另设 `GISCUS_CATEGORY` 为实际分类名称。
5. 在 Actions 中选择 **Run workflow → codex/quarto-guide** 手动部署，验证至少两篇文章下方出现中文评论组件和 GitHub 登录入口，且关联不同的讨论标识。当前预览无需修改或合并 `main`；正式版本之后可从 `main` 发布。

当前配置的公开变量为：

| 变量 | 值 |
| --- | --- |
| `GISCUS_REPO_ID` | `R_kgDOH1Ttsw` |
| `GISCUS_CATEGORY_ID` | `DIC_kwDOH1Tts84CQ6ob` |
| `GISCUS_CATEGORY` | `Announcements` |

GitHub App 安装、Discussions 和 Actions variables 是仓库级设置，不属于某一个分支；正文和工作流的修改仍在预览分支中。App 安装时选择 **Only select repositories**，仅授权 `xp_pgrs_unofficial_guide`。变量已存在不代表 App 已安装，应在 [giscus 配置页](https://giscus.app/zh-CN)填写仓库全名确认可用。

未设置 Giscus 变量时，网页仍可阅读，文章显示通往 GitHub Discussions 的链接；不要用示例 ID 冒充已启用评论。若开始配置但两个 ID 不齐，构建会报错，避免静默发布失效的评论区。分支和 fork PR 的构建不依赖任何 secret，完全缺失评论配置也应通过构建。

评论按文章 frontmatter 的 `discussion-id` 关联，使用 giscus 的固定 term 和严格匹配。新文章必须分配唯一 ID，改标题、移动文件时保留原 ID。不要为所有文章使用同一个 ID，也不要重命名已关联 Discussion 的匹配标识。删除内容时保留原讨论，便于追溯。

初次部署时没有对应 Discussion 属于正常情况；giscus 会在读者第一次留言或回应时自动建帖。严格匹配依赖正文中的 SHA-1 标识，让 giscus 自动创建即可，无需手工预建帖子或发布测试留言。构建会核对每篇文章实际生成的仓库、分类、固定标识、严格匹配和中文界面设置，防止不同页面误用同一讨论。

本地测试评论可以临时在运行环境设置 `GISCUS_REPO_ID`、`GISCUS_CATEGORY_ID`（以及可选 `GISCUS_CATEGORY`）再构建。ID 不是密码，但不要把 GitHub 登录令牌写入网页、源文件或日志。

## 本地依赖与构建

安装 [Quarto 1.10.19](https://github.com/quarto-dev/quarto-cli/releases/tag/v1.10.19)、Python 3.12 和 `requirements-build.txt`。Ubuntu 的 PDF 依赖与 CI 一致：

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends texlive-xetex texlive-lang-chinese texlive-latex-extra texlive-fonts-recommended texlive-plain-generic lmodern
python3 -m pip install -r requirements-build.txt
python3 scripts/build.py
```

PDF 使用 XeLaTeX 与 `ctexbook` 的 `fontset=fandol`，不依赖 macOS 系统字体。HTML 预览可用 `python3 scripts/build.py --html-only`，只查源文件用 `--check-only`。

产物包括 `xp-pgrs-unofficial-guide.pdf`、`markdown/content/*.md` 和 `llms.txt`。Quarto 1.10.19 的书籍项目尚不能依赖原生 `book.llms-txt`，当前通过构建导出 Markdown 和索引，内容仍只有一份。未来升级到包含书籍支持的稳定版后，再评估移除这一步；不要仅因配置 schema 接受该字段就认定已有产物。

## PDF Release

继续使用 `v*` 版本标签发布。先确认对应提交的完整构建成功，再推送版本标签。`Release PDF` 工作流检出该标签，重新构建，从 `book/_book/xp-pgrs-unofficial-guide.pdf` 生成旧习惯的附件名 `xp_pgrs_unofficial_guide_<去掉v的版本>.pdf`，上传到相应 GitHub Release。已有同名附件会更新。

需要补发时，在 Actions 手动运行 `Release PDF`，输入已存在的 `v*` 标签；从标签运行时可省略输入。从分支手动运行且没有标签会明确失败，不会猜测版本或创建标签。历史 LaTeX 版本标签缺少新构建入口，保留其既有 Release，不用新工作流重发。

## 投稿审核与历史归档

新作者可使用 Issue Form 填写普通文字。编辑核实署名和来源，在 `book/_authors.yml` 登记作者，将正文整理为署名块并通过 PR 审核；对代录内容保留投稿人的作者身份。稿件、评论与正式正文分开，避免未经核实的信息自动上线。

`docs/legacy-workflows/latex-to-pr.yml` 与 `docs/legacy-workflows/deploy-to-cloud.yml` 是历史参考副本，已移出 `.github/workflows/`，不会被 GitHub Actions 执行。前者不再从 LaTeX 生成第二份正文，后者不再自动操作腾讯云。该迁移不读取密钥、不删除或修改既有云资源；如需清理旧云服务，由拥有者另行处理。
