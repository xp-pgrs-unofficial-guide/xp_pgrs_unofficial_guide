-- Localized reader controls, contribution links and a stable shared discussion.
local meta
local function value(v) return v and pandoc.utils.stringify(v) or "" end
local function html(s)
  return s:gsub("&", "&amp;"):gsub('"', "&quot;"):gsub("<", "&lt;"):gsub(">", "&gt;")
end
local function uri(s)
  return (s:gsub("([^A-Za-z0-9%-_%.~])", function(c) return string.format("%%%02X", string.byte(c)) end))
end
local function uri_path(s) return uri(s):gsub("%%2F", "/") end
return {
  {Meta = function(m) meta = m end},
  {Link = function(link)
    if FORMAT:match("latex") and not link.target:match("^%a[%w+.-]*:") then
      local target = pandoc.path.normalize(link.target)
      while target:sub(1, 3) == "../" do target = target:sub(4) end
      if target:match("^assets/") then
        link.target = value(meta["guide-site-root"] or meta["guide-site"]) .. target
        return link
      elseif target == "llms.txt" then
        link.target = value(meta["guide-site"]) .. target
        return link
      end
    end
  end},
  {Pandoc = function(doc)
    if not FORMAT:match("html") then return doc end
    local repo, site = value(meta["guide-repo"]), value(meta["guide-site"])
    if repo == "" then return doc end
    local english = value(meta.lang):match("^en") ~= nil
    local function text(zh, en) return english and en or zh end
    local branch = value(meta.book and meta.book["repo-branch"])
    if branch == "" then error("[publishing] book.repo-branch is required for article contribution links") end
    local input = quarto.doc.input_file
    if type(input) == "function" then input = input() end
    input = tostring(input):gsub("\\", "/"):gsub("^.-/book/en/", ""):gsub("^.-/book/", ""):gsub("^book/en/", ""):gsub("^book/", "")
    local page = input:gsub("%.qmd$", ".html")
    local target = site .. uri_path(page)
    local source = value(meta["guide-source-prefix"]) .. input
    local title, discussion = value(meta.title), value(meta["discussion-id"])
    local body = table.concat({
      text("### 文章信息", "### Article information"),
      text("标题：", "Title: ") .. title,
      text("链接：", "URL: ") .. target,
      text("源文件：", "Source: ") .. "book/" .. source,
      text("源分支：", "Branch: ") .. branch,
      text("文章标识：", "Discussion ID: ") .. discussion,
      "", text("### 补充内容／纠错", "### Addition or correction"),
      text("请说明具体位置、建议内容及适用时间，可附图片或文件。", "Describe the location, proposed change and applicable date. Images or files are welcome."),
      "", text("### 公开署名／昵称", "### Public name or pseudonym"),
      text("请填写希望公开的署名；需要匿名请填“匿名”。", "Enter the name to credit publicly, or write anonymous."),
      "", text("### 来源与核实时间", "### Source and date checked"),
      text("请提供参考链接或亲身经历的时间。", "Provide a reference or the date of your first-hand experience.")
    }, "\n")
    local issue = repo .. "/issues/new?title=" .. uri(text("[补充／纠错] ", "[Addition / correction] ") .. title) .. "&body=" .. uri(body)
    local edit = repo .. "/edit/" .. uri_path(branch) .. "/book/" .. uri_path(source)
    local depth = select(2, input:gsub("/", "/"))
    local relative = string.rep("../", depth)
    local markdown = relative .. "markdown/" .. input:gsub("%.qmd$", ".md")
    local root_site = value(meta["guide-site-root"])
    if root_site == "" then root_site = site end
    local alternate = root_site .. (english and "" or "en/") .. uri_path(page)
    local controls = '<nav class="guide-reading-controls" aria-label="' .. text("阅读语言", "Reading language") .. '">'
      .. '<span aria-current="true" lang="' .. (english and 'en' or 'zh-CN') .. '">' .. (english and 'English' or '中文') .. '</span>'
      .. '<a class="guide-language-switch no-external" data-noresolveinput target="_self" hreflang="' .. (english and 'zh-CN' or 'en') .. '" href="' .. html(alternate) .. '">' .. (english and '中文' or 'English') .. '</a></nav>'
    if english and value(meta["translation-status"]) == "draft" then
      controls = controls .. '<p class="guide-translation-note">English translation draft, awaiting human review. Original author credits and historical dates are retained. <a class="guide-language-switch no-external" target="_self" href="' .. html(alternate) .. '">Read the Chinese source</a>.</p>'
    end
    doc.blocks:insert(1, pandoc.RawBlock("html", controls))
    local parts = {
      '<section class="guide-downloads" aria-label="' .. text("PDF 下载", "PDF downloads") .. '">',
      '<h2 class="unnumbered">' .. text("下载整本攻略", "Download the full guide") .. '</h2>',
      '<nav class="guide-actions" aria-label="' .. text("下载入口", "Download options") .. '">',
      '<a class="guide-pdf-download no-external" hreflang="zh-CN" href="' .. html(root_site .. 'xp-pgrs-unofficial-guide.pdf') .. '">' .. text("中文版 PDF", "Chinese PDF") .. '</a>',
      '<a class="guide-pdf-download no-external" hreflang="en" href="' .. html(root_site .. 'en/xp-pgrs-unofficial-guide.pdf') .. '">English PDF</a>',
      '<a href="' .. html(repo .. '/releases/latest') .. '">' .. text("版本归档（Release）", "Versioned releases") .. '</a></nav></section>',
      '<section class="guide-participate" aria-label="' .. text("参与完善本页", "Improve this page") .. '">',
      '<h2 class="unnumbered">' .. text("一起完善这一页", "Help improve this page") .. '</h2>',
      '<p>' .. text("分享变化、补充经验，或帮我们修正一处错误。正文由编辑审核后发布。", "Share an update, add your experience, or correct an error. Editors review changes before publication.") .. '</p>',
      '<nav class="guide-actions" aria-label="' .. text("供稿入口", "Contribution options") .. '">',
      '<a href="' .. html(issue) .. '">' .. text("补充内容／纠错", "Add or correct content") .. '</a>',
      '<a href="' .. html(edit) .. '">' .. text("提出修改（PR）", "Propose an edit (PR)") .. '</a>',
      '<a data-noresolveinput href="' .. html(markdown) .. '">' .. text("纯 Markdown", "Plain Markdown") .. '</a></nav>',
      '<p class="guide-contribution-help">' .. text("“补充内容／纠错”已带上文章信息，填写建议后提交即可。也可选择“提出修改（PR）”在 GitHub 网页编辑；无仓库写权限时，按提示创建 fork 并提交 PR，目标分支选择 ", "The contribution draft includes this page’s details. You can also edit on GitHub; without write access, follow the fork and pull request prompts. Target branch: ") .. '<code>' .. html(branch) .. '</code>' .. text('。', '.') .. '</p>',
      '</section><section class="guide-discussion" aria-label="' .. text("文章讨论", "Article discussion") .. '"><h2 class="unnumbered">' .. text("讨论", "Discussion") .. '</h2>'
    }
    local repoid, categoryid = os.getenv("GISCUS_REPO_ID") or "", os.getenv("GISCUS_CATEGORY_ID") or ""
    if repoid ~= "" and categoryid ~= "" and discussion ~= "" then
      parts[#parts + 1] = '<p>' .. text("使用 GitHub 账号登录后即可留言；评论保存在本仓库的 Discussions。", "Sign in with GitHub to comment. Comments are stored in this repository’s Discussions.") .. '</p>'
      local category = os.getenv("GISCUS_CATEGORY") or ""
      if category == "" then category = "文章评论" end
      parts[#parts + 1] = '<script src="https://giscus.app/client.js" data-repo="' .. html(repo:gsub("^https://github.com/", ""))
        .. '" data-repo-id="' .. html(repoid) .. '" data-category="' .. html(category) .. '" data-category-id="' .. html(categoryid)
        .. '" data-mapping="specific" data-term="' .. html(discussion) .. '" data-strict="1" data-reactions-enabled="1" data-emit-metadata="0" data-input-position="top"'
        .. ' data-theme="preferred_color_scheme" data-lang="' .. (english and 'en' or 'zh-CN') .. '" data-loading="lazy" crossorigin="anonymous" async></script>'
    else
      parts[#parts + 1] = '<p>' .. text("欢迎到 GitHub Discussions 讨论本页，并附上文章链接。", "Discuss this page on GitHub Discussions and include the article URL.") .. '</p>'
    end
    parts[#parts + 1] = '<p><a href="' .. html(repo .. "/discussions") .. '">' .. text("在 GitHub 打开讨论", "Open GitHub Discussions") .. '</a></p></section>'
    parts[#parts + 1] = '<script src="' .. html(relative .. (english and "../" or "") .. 'assets/guide.js') .. '"></script>'
    doc.blocks:insert(pandoc.RawBlock("html", table.concat(parts, "\n")))
    return doc
  end}
}
