-- Shared, validated records supply the same reader-facing timeline in every
-- output. Placeholders also survive Quarto's combined PDF chapter input.
local function value(v) return v and pandoc.utils.stringify(v) or "" end

local function page_path(meta)
  local input = value(meta["guide-page-path"])
  if input == "" and quarto and quarto.doc then
    input = quarto.doc.input_file
    if type(input) == "function" then input = input() end
    input = tostring(input):gsub("\\", "/"):gsub("^.-/book/en/", "")
      :gsub("^.-/book/", ""):gsub("^book/en/", ""):gsub("^book/", "")
  end
  return input ~= "" and input or "content/about/changelog.qmd"
end

local function relative_path(target, source)
  local from, to = {}, {}
  for part in source:gmatch("[^/]+") do from[#from + 1] = part end
  table.remove(from) -- Source paths include the current page filename.
  for part in target:gmatch("[^/]+") do to[#to + 1] = part end
  while #from > 0 and #to > 0 and from[1] == to[1] do
    table.remove(from, 1)
    table.remove(to, 1)
  end
  return string.rep("../", #from) .. table.concat(to, "/")
end

local function article_path(target, source)
  if quarto and quarto.doc then
    -- Quarto rebases metadata fields named `path` from the project root to
    -- the current input file before running filters. Restore the shared
    -- root-relative representation before calculating our canonical link.
    local combined = source:match("^(.*)/")
    combined = (combined and (combined .. "/") or "") .. target
    local parts = {}
    for part in combined:gmatch("[^/]+") do
      if part == ".." and #parts > 0 and parts[#parts] ~= ".." then
        table.remove(parts)
      elseif part ~= "." then
        parts[#parts + 1] = part
      end
    end
    target = table.concat(parts, "/")
  end
  return relative_path(target, source)
end

return {{Pandoc = function(doc)
  local placeholders = false
  doc:walk({Div = function(div)
    if div.classes:includes("guide-updates") then placeholders = true end
  end})
  if not placeholders then return doc end
  local records = doc.meta["guide-updates"]
  if not records then error("[updates] Missing guide-updates metadata. Generate the update records before rendering.", 0) end
  local english = value(doc.meta.lang):match("^en") ~= nil
  local language = english and "en" or "zh-CN"
  local html = FORMAT:match("html") ~= nil
  local pdf = FORMAT:match("latex") ~= nil
  local source = page_path(doc.meta)
  local month_names = {"January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"}
  local function contribution(blocks, identifier)
    -- Attribution unwraps non-HTML blocks. Keep a separate destination inside
    -- them so PDF and Markdown retain the same event links as the website.
    if not html and identifier then
      local safe = identifier:gsub("&", "&amp;"):gsub('"', "&quot;")
        :gsub("<", "&lt;"):gsub(">", "&gt;")
      table.insert(blocks, 1, pdf and pandoc.Div({}, pandoc.Attr(identifier))
        or pandoc.RawBlock("html", '<a id="' .. safe .. '"></a>'))
    end
    return pandoc.Div(blocks, pandoc.Attr(html and (identifier or "") or "",
      {"contribution", "guide-update"}, {authors="editorial"}))
  end
  local function render()
    local blocks, current_month = pandoc.Blocks({}), nil
    for _, record in ipairs(records) do
      local date, kind = value(record.date), value(record.type)
      local month = date:sub(1, 7)
      if month ~= current_month then
        local year, number = month:match("^(%d%d%d%d)%-(%d%d)$")
        local title = english and (month_names[tonumber(number)] .. " " .. year)
          or (year .. " 年 " .. tonumber(number) .. " 月")
        blocks:insert(pandoc.Header(3, {pandoc.Str(title)}, pandoc.Attr("updates-" .. month)))
        current_month = month
      end
      local kind_label = kind == "content" and (english and "Content update" or "内容更新")
        or (english and "Site improvement" or "网站改进")
      local dateline = html and {
        pandoc.Span({pandoc.Str(date)}, pandoc.Attr("", {"guide-update-date"})),
        pandoc.Str(" · "),
        pandoc.Span({pandoc.Str(kind_label)}, pandoc.Attr("", {"guide-update-kind", kind}))
      } or {pandoc.Strong({pandoc.Str(date .. " · " .. kind_label)})}
      local summary = {pandoc.Str(value(record.summary[language]))}
      local event = {
        pandoc.Para(dateline),
        pandoc.Para(html and {pandoc.Span(summary, pandoc.Attr("", {"guide-update-summary"}))} or summary)
      }
      if record.articles and #record.articles > 0 then
        local links = pandoc.Inlines({pandoc.Str(english and "Related articles: " or "相关文章：")})
        for i, article in ipairs(record.articles) do
          if i > 1 then links:insert(pandoc.Str(english and ", " or "、")) end
          local target = "#" .. value(article.anchor)
          if not pdf then target = article_path(value(article.path), source) .. target end
          links:insert(pandoc.Link({pandoc.Str(value(article.title[language]))}, target))
        end
        event[#event + 1] = pandoc.Para(html and {pandoc.Span(links, pandoc.Attr("", {"guide-update-links"}))} or links)
      end
      blocks:insert(contribution(event, "update-" .. value(record.id)))
    end
    if #records == 0 then
      blocks:insert(contribution({pandoc.Para({pandoc.Str(english and "No updates recorded yet." or "暂无更新记录。")})}))
    end
    return blocks
  end
  return doc:walk({Div = function(div)
    if div.classes:includes("guide-updates") then return render() end
  end})
end}}
