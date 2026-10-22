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

`book/index.qmd` 保留为首页和新手导航，其余文章放在 `book/content/` 下的六个主题目录与一个辅助目录中：

| 英文文件夹 | 中文目录主题与边界 |
| --- | --- |
| `academic/` | 学业：博士项目制度、培养要求、考核、学位取得与证明材料 |
| `resources/` | 资源：可以申请或使用的服务、设施、经费、软件和文献入口 |
| `research/` | 研究：科研方法、过程、资料管理与学术交流、访学 |
| `work/` | 工作：助教、监考等岗位经验，以及职业发展 |
| `life/` | 生活：日常事务、身心健康、运动与娱乐 |
| `social/` | 社交：组织社团、同伴互助和人际交流 |
| `about/` | 关于本指南：前言、供稿与纠错、项目建设、致谢和更新日志 |

每篇文章只有一个主要归属，相关栏目通过链接提供入口。资源按用途分类，西浦、利物浦或校外等来源在正文中注明。访学文章集中在研究专题，生活和资源目录可提供相关链接。待补导览应明确说明缺少哪些实质内容，并提供征稿入口，不能让规划选题看起来像已有完整攻略。

新增文章放入相应主题目录，例如 `book/content/academic/`。网站阅读顺序由 `book/_quarto.yml` 的显式目录决定，采用“一级主题 → 二级专题 → 具体文章”三级结构；文件夹和文件名的排序不改变导航顺序。顶层使用 `part/contents`，内部专题使用 `section/contents`，例如：

```yaml
book:
  chapters:
  - index.qmd
  - part: 学业
    contents:
    - section: 培养要求与考核
      contents:
      - content/academic/apr.qmd
```

构建递归发现正文和 `book/authors/` 下的 `.qmd`，检查每种语言的首页、文章和作者页是否被目录完整覆盖，以及是否有重复条目。英文目录从共享配置生成；PDF 专用配置按相同顺序展开子文章，仅保留一级主题及辅助分组，不把网页的二级专题再生成为分卷。生成的英文配置和 PDF 专用配置不手工维护或提交。

移动或改名时，同步移动 `book/en/` 中的对应译文，保留文章的 `discussion-id`、页首稳定锚点、段落锚点以及作者和补充者 ID。同步更新共享目录、正文相对引用、译文来源路径与哈希，以及 `book/redirects.yml`。别名表记录“旧 `.qmd` 路径 → 当前 `.qmd` 路径”；历史别名应直接指向文件现在的位置，避免多次跳转。移动后核对图片和附件的相对路径；`legacy-source` 指向的历史原稿路径保持不变。

拆分文章时，原页保留流程或入门正文，继续使用原讨论标识，并在旧小节锚点处链接到新文章。新文章分配新的 `discussion-id` 和页首锚点；移出的标题使用带主题前缀的新锚点，避免旧页和新页在整本 PDF 中出现重复定位标识。实际正文、作者块、段落锚点和资料日期随内容移动，不在导览页复制；新增衔接说明按实际整理者署名。中英文同时拆分，并核对内容和附件没有遗漏。

合并文章时，目标页保留选定主文章的讨论标识，以及被合并页面的旧页首锚点，并为各旧地址登记跳转。评论保存在 GitHub Discussions 中，不会因正文合并而自动迁移或合并；若旧页已有独立讨论，应在目标页保留其入口。

构建根据别名表生成旧 HTML 地址的跳转页，保留访问时的查询参数和锚点；旧 Markdown 地址生成迁移提示并指向当前文章。这些是生成物，旧位置不保留第二份 `.qmd` 正文。按下文运行检查和预览，确认旧地址及小节入口可用后，再提交 PR。

## 双语正文与翻译维护

中英文文章按相同相对路径对应，例如 `book/content/academic/apr.qmd` 与 `book/en/content/academic/apr.qmd`。两边使用相同的 `discussion-id`、显式锚点和署名块，网页切换语言后仍对应同一篇文章与讨论。译文需完整保留原内容的条件、日期、链接和作者，不因翻译改写历史事实。

英文 frontmatter 除标题、讨论标识和历史来源外，还包含：

```yaml
lang: en
translation-source: content/academic/apr.qmd
translation-source-sha256: 中文源文件原始字节的SHA256
translation-status: draft
```

`draft` 表示英文初稿待人工复核，`reviewed` 表示已复核。中文修改后，先核对差异并同步译文，再更新来源哈希；已复核译文发生实质变化时，先改回 `draft`，复核后再恢复。构建会拒绝缺少对应页面、来源哈希过期、署名或显式锚点不一致的译文。不能只更新哈希来掩盖未翻译的修改。计算来源哈希可用：

```sh
python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('book/content/academic/apr.qmd').read_bytes()).hexdigest())"
```

本地图片仍共用 `book/assets/`；英文文件引用时须按自身位置调整相对路径。标题层级和段落应与中文对应；为两边的小节标题显式填写相同的 `{#稳定标识}`，构建会检查标题定位一致。新增文章需同时补充对应译文；若需帮助，可先提交 Issue，由编辑协助整理。

共享目录和输出设置维护于 `book/_quarto.yml`，英文书名和目录主题译名维护于 `book/_languages.yml`。`book/en/_quarto.yml`、PDF 专用扁平章节配置和 `book/_updates.generated.yml` 是构建生成物，不手工编辑或提交。

## 更新记录

新文章、重要经验补充、实质纠错，以及目录、搜索、评论等读者可感知的网站改进，应在 `book/updates/` 新增一个小 YAML 文件。每次逻辑上独立的变化写一条记录，可关联多篇文章；中文修改与对应英文同步共用一条。错字、排版、常规翻译同步、来源哈希和内部构建调整通常省略，无需每次提交都新增记录，也无需为日常更新升级版本号。

文件名采用日期和简短主题，例如 `2026-10-22-apr-advice.yml`；以下内容可复制后按实际变化修改：

```yaml
date: 2026-10-22
type: content
summary:
  zh-CN: 补充年度进展评审的准备经验。
  en: Add practical preparation advice for the annual progress review.
articles:
  - xp-guide-apr
```

`date` 由编辑填写，格式为 `YYYY-MM-DD`，表示这次变化的日期，不是文中事实的核验日期。`type` 只使用 `content`（内容更新）或 `site`（网站改进）；摘要各用中英文一句话说明读者能看到的变化。`articles` 填文章页首的稳定标识，通常与 `discussion-id` 相同；内容更新至少关联一篇文章，全站性网站改进可写 `articles: []`。文章移动或改名时保留稳定标识，合并时在承接页保留旧页首锚点，已有记录便能继续定位；显示标题和链接由构建按当前文章自动解析。

同一份记录自动汇总到集中更新页的中英文版本，并进入 PDF 和 Markdown；首页和文章页不增加更新组件。原有六条手工版本记录保留为历史里程碑。不要直接编辑生成的近期更新列表或 `book/_updates.generated.yml`，构建不会把生成内容写回正文源文件，也不依赖 Git 历史或外部服务。CI 会校验已有记录的日期、类型、双语摘要和文章标识；是否需要为一次修改新增记录，由编辑和审稿人判断。

## 段落署名与写作格式

作者登记在 `book/_authors.yml`，`guide-authors` 和 `guide-authors-en` 分别提供中英文公开显示名，两者使用相同的稳定 ID。首次投稿由编辑登记 ID；不要把邮箱、学号等非必要资料放入作者表。新内容必须填写真实作者或明确约定的匿名署名，不能使用历史内容的待确认作者占位值。

正文按实际作者划分为相邻的 `.contribution` 块。小节标题（`##`、`###` 等）用于导航，放在署名块外，以便 Quarto 正常生成页内目录；标题本身无需单独署名。一个块可以包含同一作者连续撰写的多段文字、列表、表格和图片；遇到下一个标题时先关闭当前块，在标题之后重新开块，作者变化时也另起一块。不要嵌套署名块。网页会将连续且原作者、补充者、确认状态均一致的内容合用一个右侧作者图标，跨标题的相同署名也适用，遇到变化另显示一个。图标随滚动停留在对应内容范围内；悬停、键盘聚焦或点击时显示署名并高亮范围，手机上可轻点。按 Escape 或点击外部可关闭。源文件仍需逐块标记，Markdown 继续逐块输出署名。PDF 在每章内将连续且原作者、补充者、确认状态相同的内容合并显示一次署名，跨小节也适用；任一项变化、切回先前署名或进入新章时，重新显示署名。不要为了显示去重而删掉源署名。

正文不再手写姓名落款、`by …` 或“某某更新”等重复署名，统一由块属性生成。资料日期、适用时间和更新依据仍可写在正文中，并和其他正文一样放入实际提供者的署名块内；不要因移动标题而把这些段落留在块外。引用来源、致谢对象和有用的联系信息按内容需要保留。

以下用已登记的两个作者 ID 演示相邻署名块。示例中的文字和 ID 应按实际内容及作者替换：

```markdown
## 主题标题 {#your-topic}

::: {#p-your-topic-001 .contribution authors="shiyao-zhang"}

这里写经确认由张世尧提供的内容。

同一作者接着写的下一段也可以放在这个块里。

:::

### 另一部分 {#your-subtopic}

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

作者清单直接显示在目录的“作者与贡献者”分组下，选择姓名即可进入对应主页。该上级条目仅用于展开与折叠分组，没有独立清单页。各主页位于 `book/authors/`，英文页位于 `book/en/authors/`，使用 `book/filters/author-pages.lua` 中的统一模板，依据现有 `.contribution` 的 `authors` 与 `contributors` 自动汇总参与文章，不根据 Git 提交者推断作者，也不推断个人简介。“归属待确认”是历史材料的归属标记，不代表某位作者。旧清单网址 `/authors/` 和 `/authors/index.html` 会跳转到首页的作者导航说明。

登记新作者时，在作者表补充两种语言的显示名，并参照已有作者页添加中英文页面及共享章节目录条目。作者页仅保留 frontmatter、稳定页首锚点和署名块内的 `.guide-author-profile` 占位 Div，`data-guide-author-id` 填作者 ID；不要复制通用说明或资料列表。网页、Markdown 和整本 PDF 都由同一模板原位生成资料与参与文章。编辑组和待确认身份的说明也由模板按 `type` 统一生成。公开简介、机构等个人内容只维护作者表，且仅在本人提供或确认后填写。

公开资料统一维护在 `book/_authors.yml` 的 `guide-author-profiles`，以同一个作者 ID 索引；作者和实质补充者共用这套资料。作者主页会自动展示已填写的资料，网页、PDF、Markdown 使用同一来源。作者页不显示正文右侧的署名图标，以免将页面整理者误认为该页介绍的作者。例如现有项目身份：

```yaml
guide-author-profiles:
  shiyao-zhang:
    type: person
    project-roles: [编辑]
    project-roles-en: [Editor]
```

可按需要补充以下字段。未知项直接省略，不填 `null`、空字符串、示例账号或同名者的链接。

| 字段 | 内容与格式 |
| --- | --- |
| `type` | `person`（默认）、`team` 或 `placeholder`；编辑组和待确认标记分别使用后两者 |
| `project-roles` / `project-roles-en` | 项目角色，成对的中文／英文字符串列表 |
| `affiliation` / `affiliation-en` | 机构名称，成对的中文／英文文本 |
| `department` / `department-en` | 部门或院系，成对的中文／英文文本 |
| `research-interests` / `research-interests-en` | 研究方向，成对的中文／英文字符串列表 |
| `bio` / `bio-en` | 简短公开简介，成对的中文／英文文本 |
| `orcid` | 带连字符的 16 位 ORCID iD，末位可为大写 `X`；构建校验格式与校验位 |
| `google-scholar` | 本人的完整 `https://scholar.google.com/citations?user=…` 链接 |
| `website` | 个人主页的完整 HTTPS 链接 |
| `institutional-profile` | 机构个人资料页的完整 HTTPS 链接 |
| `github` | 本人的完整 `https://github.com/…` 主页链接 |
| `email` | 希望公开的纯邮箱地址，不加 `mailto:`；两种语言共用，展示为可点击的联系链接 |

机构、研究方向和简介应由本人提供或确认；资料变动后更新相应字段，不依据旧邮箱推断当前任职机构。机构等中英文展示字段一起填写，账号链接两种语言共用。没有学术资料时，作者页只显示简短的待补充提示，不生成空链接；`team` 与 `placeholder` 不填写个人 ORCID 或 Scholar。

作者主页和正文右侧的署名浮窗共用这套资料；浮窗中原作者与实质补充者各自显示已登记的学术、联系图标，无资料时只显示姓名。悬停或键盘聚焦图标可查看名称与地址，点击即可访问，邮箱图标会打开邮件应用。PDF、Markdown 与网页打印保留可读文字和链接。

补充资料可从作者页下方“补充内容／纠错”提交作者 ID 和希望公开的字段，或提交修改作者表的 PR。构建会在发布前检查作者 ID、字段类型、双语配对、ORCID 校验位和链接格式；格式通过不代表身份已核实，维护者仍需核对本人确认。

## 本地检查与预览

Python 3.12 与 Quarto 1.10.19：

```sh
python3 -m pip install -r requirements-build.txt
python3 scripts/build.py --check-only
python3 scripts/build.py --html-only
quarto preview book
```

运行构建后，也可用 `quarto preview book/en` 预览英文。修改 `book/updates/` 的记录后，需重新运行 `python3 scripts/build.py --html-only` 再预览，以刷新生成的更新数据。完整构建同时生成两种语言的 PDF、Markdown 和检索索引，还需要包含 ctex、Fandol 字体的 XeLaTeX 环境：

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

预览时核对三级目录的展开折叠与当前文章标示、待补导览的明确提示、旧文章和旧小节入口，以及系统默认主题、手动切换、同篇语言切换、作者链接和连续署名的显示。署名图标需检查长内容滚动、作者交界、键盘操作和窄屏轻点，确认高亮范围与源块一致。需要 PDF 时运行 `python3 scripts/build.py`，使构建生成的扁平章节配置生效；网页预览继续使用上述 `quarto preview` 命令。PDF 样式修改需完整构建并检查封面、目录和正文页。

Pull Request 请说明改动主题、资料来源及作者归属，并检查本次变化是否需要[更新记录](#更新记录)。有记录时，预览集中更新页的中英文摘要、相关文章和窄屏换行。CI 会验证源文件和已有更新记录，并构建网页、PDF 和纯 Markdown，输出可从 Actions 的 `guide-build` artifact 下载。不要把 `book/_book/`、生成配置或缓存文件提交到仓库。
