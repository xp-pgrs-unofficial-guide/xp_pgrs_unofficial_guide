-- Author directories derive credits from source blocks, never from Git history.
-- Explicit source placeholders also work when Quarto combines chapters for PDF.
local function value(v) return v and pandoc.utils.stringify(v) or "" end
local function has_class(div, name) return div.classes:includes(name) end
return {{Pandoc = function(doc)
  local has_placeholders = false
  doc:walk({Div = function(div)
    if has_class(div, "guide-author-profile") or has_class(div, "guide-author-index") then
      has_placeholders = true
    end
  end})
  local legacy_id = value(doc.meta["guide-author-id"])
  if not has_placeholders and legacy_id == "" and not doc.meta["guide-author-index"] then return doc end
  local english = value(doc.meta.lang):match("^en") ~= nil
  local pdf = FORMAT:match("latex") ~= nil
  local names = (english and doc.meta["guide-authors-en"]) or doc.meta["guide-authors"]
  local root = value(doc.meta["guide-source-root"])
  if root == "" and quarto and quarto.project then root = quarto.project.directory end
  if root == "" then error("[authors] Missing project root") end
  local paths = {}
  local function chapters(node)
    if not node then return end
    local kind = pandoc.utils.type(node)
    if type(node) == "string" or kind == "Inlines" then
      local text = value(node)
      if text:match("%.qmd$") then paths[#paths + 1] = text end
    elseif node.chapters then chapters(node.chapters)
    elseif type(node) == "table" then for _, child in ipairs(node) do chapters(child) end end
  end
  chapters(doc.meta.book and doc.meta.book.chapters)
  -- Read sources once per document, then reuse the credits for every placeholder.
  local credits = {}
  for _, path in ipairs(paths) do
    if path == "index.qmd" or path:match("^content/") then
      local file = assert(io.open(root .. "/" .. path, "r"))
      local source = pandoc.read(file:read("*a"), "markdown")
      file:close()
      local people = {}
      source:walk({Div = function(div)
        if not has_class(div, "contribution") then return end
        for _, field in ipairs({"authors", "contributors"}) do
          for person in tostring(div.attributes[field] or ""):gmatch("[^,%s]+") do
            people[person] = people[person] or {}
            people[person][field] = true
            if div.attributes.status == "unverified" then people[person].uncertain = true end
          end
        end
      end})
      for person, roles in pairs(people) do
        credits[person] = credits[person] or {}
        table.insert(credits[person], {path=path, title=value(source.meta.title),
          discussion=value(source.meta["discussion-id"]), roles=roles})
      end
    end
  end
  local function render(id)
    local blocks = pandoc.Blocks({})
    if id == "" then
      local ids = {}
      for person in pairs(names) do if person ~= "unknown" then ids[#ids + 1] = person end end
      table.sort(ids)
      local items = {}
      for _, person in ipairs(ids) do
        local target = pdf and ("#xp-guide-author-" .. person) or (person .. ".qmd")
        items[#items + 1] = {pandoc.Plain({pandoc.Link({pandoc.Str(value(names[person]))}, target), pandoc.Str(" — " .. #(credits[person] or {}) .. (english and " articles" or " 篇文章"))})}
      end
      blocks:insert(pandoc.BulletList(items))
      blocks:insert(pandoc.Header(2, english and "Historical attribution" or "历史归属", pandoc.Attr("historical-attribution")))
      local target = pdf and "#xp-guide-author-unknown" or "unknown.qmd"
      blocks:insert(pandoc.Para({pandoc.Link({pandoc.Str(english and "Content awaiting attribution" or "查看归属待确认的内容")}, target)}))
    else
      if not names[id] then error("[authors] Unknown profile ID " .. id) end
      blocks:insert(pandoc.Header(2, english and "Credited articles" or "参与文章", pandoc.Attr("credited-articles-" .. id)))
      local items = {}
      for _, credit in ipairs(credits[id] or {}) do
        local labels = {}
        if credit.roles.authors then labels[#labels + 1] = english and "original author" or "原作者" end
        if credit.roles.contributors then labels[#labels + 1] = english and "substantive additions" or "实质补充" end
        if credit.roles.uncertain then labels[#labels + 1] = english and "attribution requires confirmation" or "具体归属待确认" end
        local target = pdf and ("#" .. credit.discussion) or ("../" .. credit.path)
        items[#items + 1] = {pandoc.Plain({pandoc.Link({pandoc.Str(credit.title)}, target), pandoc.Str(" — " .. table.concat(labels, "；"))})}
      end
      if #items > 0 then blocks:insert(pandoc.BulletList(items))
      else blocks:insert(pandoc.Para({pandoc.Str(english and "No confirmed article credits are recorded yet." or "当前尚无已登记的文章署名。") })) end
      local target = pdf and "#xp-guide-authors" or "index.qmd"
      blocks:insert(pandoc.Para({pandoc.Link({pandoc.Str(english and "All authors and contributors" or "返回作者与贡献者清单")}, target)}))
    end
    return blocks
  end
  if has_placeholders then
    return doc:walk({Div = function(div)
      local profile = has_class(div, "guide-author-profile")
      local index = has_class(div, "guide-author-index")
      if not profile and not index then return end
      local id = profile and tostring(div.attributes["data-guide-author-id"] or "") or ""
      if profile and id == "" then error("[authors] Profile placeholder needs data-guide-author-id") end
      div.content = render(id)
      if FORMAT:match("html") then
        div.classes = div.classes:filter(function(name) return name ~= "guide-author-profile" and name ~= "guide-author-index" end)
        div.classes:insert("guide-author-expanded")
      else
        -- Plain Markdown and PDF need no web presentation classes or data fields.
        div.classes = pandoc.List({})
        div.attributes = {}
      end
      return div
    end})
  end
  -- Compatibility for old standalone sources without explicit placeholders.
  doc.blocks:insert(pandoc.Div(render(legacy_id), pandoc.Attr("", {"contribution"}, {authors="editorial"})))
  return doc
end}}
