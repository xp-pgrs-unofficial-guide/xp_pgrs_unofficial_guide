-- A contribution describes editorial attribution, never Git commit ownership.
-- Keep this as a Pandoc filter so the source remains readable Markdown and the
-- same attribution survives HTML, PDF and plain Markdown exports.
local registry = {}

local function fail(message)
  error("[attribution] " .. message, 0)
end

local function has_class(element, wanted)
  for _, class in ipairs(element.classes or {}) do
    if class == wanted then return true end
  end
  return false
end

local function read_registry(meta)
  local authors = meta["guide-authors"]
  if authors then
    for identifier, value in pairs(authors) do
      registry[identifier] = pandoc.utils.stringify(value)
    end
  end
  return meta
end

local function read_people(value, required)
  local identifiers, names, seen = {}, {}, {}
  for identifier in tostring(value or ""):gmatch("[^,%s]+") do
    if not registry[identifier] then
      fail("Unknown author ID '" .. identifier .. "'. Add it to book/_authors.yml.")
    end
    if not seen[identifier] then
      seen[identifier] = true
      identifiers[#identifiers + 1] = identifier
      names[#names + 1] = registry[identifier]
    end
  end
  if required and #names == 0 then
    fail("Every .contribution block needs an explicit authors attribute (use unknown when uncertain).")
  end
  return identifiers, names
end

local function html_escape(value)
  return tostring(value):gsub("&", "&amp;"):gsub("<", "&lt;")
    :gsub(">", "&gt;"):gsub('"', "&quot;"):gsub("'", "&#39;")
end

local function label_text(names, contributors, uncertain)
  local parts = {"原作者：" .. table.concat(names, "、")}
  if #contributors > 0 then
    parts[#parts + 1] = "实质补充：" .. table.concat(contributors, "、")
  end
  if uncertain then parts[#parts + 1] = "具体段落归属待确认" end
  return table.concat(parts, "；")
end

local function attribution_html(names, contributors, uncertain)
  local rows = {'<p><strong>原作者</strong><span>' .. html_escape(table.concat(names, "、")) .. '</span></p>'}
  if #contributors > 0 then
    rows[#rows + 1] = '<p><strong>实质补充</strong><span>' .. html_escape(table.concat(contributors, "、")) .. '</span></p>'
  end
  if uncertain then
    rows[#rows + 1] = '<p class="attribution-status">具体段落归属待确认</p>'
  end
  return '<details class="paragraph-attribution">' ..
    '<summary aria-label="查看本段署名" title="查看本段署名">' ..
    '<span class="attribution-icon" aria-hidden="true">i</span>' ..
    '<span class="attribution-label">署名</span></summary>' ..
    '<div class="attribution-card" role="note">' .. table.concat(rows, "") .. '</div></details>'
end

local function decorate_blocks(blocks, marker)
  local result = pandoc.Blocks({})
  for _, block in ipairs(blocks) do
    local kind = block.t
    if kind == "BulletList" or kind == "OrderedList" then
      local items = {}
      for _, item in ipairs(block.content) do
        items[#items + 1] = decorate_blocks(item, marker)
      end
      block.content = items
      result:insert(block)
    elseif kind == "DefinitionList" then
      local entries = {}
      for _, entry in ipairs(block.content) do
        local definitions = {}
        for _, definition in ipairs(entry[2]) do
          definitions[#definitions + 1] = decorate_blocks(definition, marker)
        end
        entries[#entries + 1] = {entry[1], definitions}
      end
      block.content = entries
      result:insert(block)
    elseif kind == "BlockQuote" then
      block.content = decorate_blocks(block.content, marker)
      result:insert(block)
    elseif kind == "Div" then
      if has_class(block, "contribution") then
        fail("Nested .contribution blocks are ambiguous; use adjacent blocks instead.")
      end
      block.content = decorate_blocks(block.content, marker)
      result:insert(block)
    elseif kind == "Para" or kind == "Plain" or kind == "Figure" or
      kind == "Table" or kind == "CodeBlock" or kind == "LineBlock" then
      -- Wrap the original AST block without rewriting figures, table cells,
      -- captions or citations, leaving Quarto's cross-reference filters intact.
      result:insert(pandoc.Div({pandoc.RawBlock("html", marker), block},
        pandoc.Attr("", {"attributed-unit"})))
    else
      result:insert(block)
    end
  end
  return result
end

local function contribution(div)
  if not has_class(div, "contribution") then return nil end
  local _, names = read_people(div.attributes.authors, true)
  local _, contributors = read_people(div.attributes.contributors, false)
  local status = div.attributes.status
  if status and status ~= "unverified" then
    fail("Unsupported contribution status '" .. status .. "'.")
  end
  local uncertain = status == "unverified"
  if FORMAT:match("html") then
    div.content = decorate_blocks(div.content, attribution_html(names, contributors, uncertain))
    div.attributes.authors = nil
    div.attributes.contributors = nil
    div.attributes.status = nil
    return div
  end
  local result = pandoc.Blocks({pandoc.Para({
    pandoc.Strong({pandoc.Str("署名：")}),
    pandoc.Str(label_text(names, contributors, uncertain))
  })})
  result:extend(div.content)
  -- Unwrap to ordinary blocks in GFM/PDF: no widget markup or custom source
  -- syntax should be required to read the exported text.
  return result
end

return {{Meta = read_registry}, {Div = contribution}}
