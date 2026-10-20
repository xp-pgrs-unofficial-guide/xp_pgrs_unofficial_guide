-- Keep service configuration out of content, and do not need API calls at build time.
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
  { Meta = function(m) meta = m end },
  { Link = function(link)
    if FORMAT:match("latex") and not link.target:match("^%a[%w+.-]*:") then
      local target = pandoc.path.normalize(link.target)
      while target:sub(1, 3) == "../" do target = target:sub(4) end
      if target:match("^assets/") or target == "llms.txt" then
        link.target = value(meta["guide-site"]) .. target
        return link
      end
    end
  end },
  { Pandoc = function(doc)
    if not FORMAT:match("html") then return doc end
    local repo = value(meta["guide-repo"])
    local site = value(meta["guide-site"])
    if repo == "" then return doc end
    local branch = value(meta.book and meta.book["repo-branch"])
    if branch == "" then error("[publishing] book.repo-branch is required for article contribution links") end
    local input = quarto.doc.input_file
    if type(input) == "function" then input = input() end
    input = tostring(input):gsub("\\", "/"):gsub("^.-/book/", ""):gsub("^book/", "")
    local page = input:gsub("%.qmd$", ".html")
    local target = site .. uri_path(page)
    local title = value(meta.title)
    local discussion = value(meta["discussion-id"])
    -- Issue Forms are loaded from the default branch. A plain, prefilled Issue
    -- also works while this site's source and form exist only on a preview branch.
    local body = table.concat({
      "### 文章信息",
      "标题：" .. title,
      "链接：" .. target,
      "源文件：book/" .. input,
      "源分支：" .. branch,
      "文章标识：" .. discussion,
      "",
      "### 补充内容／纠错",
      "请说明具体位置、建议内容及适用时间，可附图片或文件。",
      "",
      "### 公开署名／昵称",
      "请填写希望公开的署名；需要匿名请填“匿名”。",
      "",
      "### 来源与核实时间",
      "请提供参考链接或亲身经历的时间。"
    }, "\n")
    local issue = repo .. "/issues/new?title=" .. uri("[补充／纠错] " .. title) .. "&body=" .. uri(body)
    local edit = repo .. "/edit/" .. uri_path(branch) .. "/book/" .. uri_path(input)
    local depth = select(2, input:gsub("/", "/"))
    local relative = string.rep("../", depth)
    local markdown = relative .. "markdown/" .. input:gsub("%.qmd$", ".md")
    local parts = {
      '<section class="guide-participate" aria-label="参与完善本页">',
      '<h2 class="unnumbered">一起完善这一页</h2>',
      '<p>分享变化、补充经验，或帮我们修正一处错误。正文由编辑审核后发布。</p>',
      '<nav class="guide-actions" aria-label="供稿入口">',
      '<a href="' .. html(issue) .. '">补充内容／纠错</a>',
      '<a href="' .. html(edit) .. '">提出修改（PR）</a>',
      '<a data-noresolveinput href="' .. html(markdown) .. '">纯 Markdown</a>',
      '</nav>',
      '<p class="guide-contribution-help">“补充内容／纠错”已带上文章信息，填写建议后提交即可。也可选择“提出修改（PR）”在 GitHub 网页编辑；无仓库写权限时，按提示创建 fork 并提交 PR，目标分支选择 <code>' .. html(branch) .. '</code>。</p>',
      '</section>',
      '<section class="guide-discussion" aria-label="文章讨论"><h2 class="unnumbered">讨论</h2>'
    }
    local repoid = os.getenv("GISCUS_REPO_ID") or ""
    local categoryid = os.getenv("GISCUS_CATEGORY_ID") or ""
    if repoid ~= "" and categoryid ~= "" and discussion ~= "" then
      parts[#parts + 1] = '<p>使用 GitHub 账号登录后即可留言；评论保存在本仓库的 Discussions。</p>'
      local reponame = repo:gsub("^https://github.com/", "")
      local category = os.getenv("GISCUS_CATEGORY") or ""
      if category == "" then category = "文章评论" end
      parts[#parts + 1] = '<script src="https://giscus.app/client.js" data-repo="' .. html(reponame)
        .. '" data-repo-id="' .. html(repoid) .. '" data-category="' .. html(category)
        .. '" data-category-id="' .. html(categoryid) .. '" data-mapping="specific" data-term="' .. html(discussion)
        .. '" data-strict="1" data-reactions-enabled="1" data-emit-metadata="0" data-input-position="top"'
        .. ' data-theme="light" data-lang="zh-CN" data-loading="lazy" crossorigin="anonymous" async></script>'
    else
      parts[#parts + 1] = '<p>欢迎到 GitHub Discussions 讨论本页，并附上文章链接。</p>'
    end
    parts[#parts + 1] = '<p><a href="' .. html(repo .. "/discussions") .. '">在 GitHub 打开讨论</a></p></section>'
    parts[#parts + 1] = '<script src="' .. html(relative .. 'assets/guide.js') .. '"></script>'
    doc.blocks:insert(pandoc.RawBlock("html", table.concat(parts, "\n")))
    return doc
  end }
}
