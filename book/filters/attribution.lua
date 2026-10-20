-- A contribution describes editorial attribution, never Git commit ownership.
-- Keep this as a Pandoc filter so the source remains readable Markdown and the
-- same attribution survives HTML, PDF and plain Markdown exports.
local registry = {}
local english = false
local previous_signature = nil
local profile_prefix = "authors/"

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
  english = pandoc.utils.stringify(meta.lang or ""):match("^en") ~= nil
  previous_signature = nil
  if quarto and quarto.doc then
    local input = quarto.doc.input_file
    if type(input) == "function" then input = input() end
    input = tostring(input):gsub("\\", "/"):gsub("^.-/book/en/", ""):gsub("^.-/book/", ""):gsub("^book/en/", ""):gsub("^book/", "")
    profile_prefix = string.rep("../", select(2, input:gsub("/", "/"))) .. "authors/"
  end
  local authors = meta["guide-authors"]
  if authors then
    for identifier, value in pairs(authors) do
      registry[identifier] = pandoc.utils.stringify((english and meta["guide-authors-en"] and meta["guide-authors-en"][identifier]) or value)
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
  local parts = {(english and "Original author: " or "原作者：") .. table.concat(names, "、")}
  if #contributors > 0 then
    parts[#parts + 1] = (english and "Substantive additions: " or "实质补充：") .. table.concat(contributors, "、")
  end
  if uncertain then parts[#parts + 1] = english and "Paragraph attribution awaiting confirmation" or "具体段落归属待确认" end
  return table.concat(parts, "；")
end

local function profile_links(ids, names)
  local links = {}
  for i, id in ipairs(ids) do
    links[#links + 1] = '<a href="' .. profile_prefix .. id .. '.html">' .. html_escape(names[i]) .. '</a>'
  end
  return table.concat(links, "、")
end

local function attribution_html(ids, names, contributor_ids, contributors, uncertain)
  local rows = {'<p><strong>' .. (english and 'Original author' or '原作者') .. '</strong><span>' .. profile_links(ids, names) .. '</span></p>'}
  if #contributors > 0 then
    rows[#rows + 1] = '<p><strong>' .. (english and 'Substantive additions' or '实质补充') .. '</strong><span>' .. profile_links(contributor_ids, contributors) .. '</span></p>'
  end
  if uncertain then
    rows[#rows + 1] = '<p class="attribution-status">' .. (english and 'Paragraph attribution awaiting confirmation' or '具体段落归属待确认') .. '</p>'
  end
  return '<details class="paragraph-attribution">' ..
    '<summary aria-label="' .. (english and 'Attribution for this continuous passage' or '查看这段连续内容的署名') .. '">' ..
    '<span class="attribution-icon" aria-hidden="true">i</span>' ..
    '<span class="attribution-label">' .. (english and 'By ' or '作者：') .. html_escape(table.concat(names, "、")) .. '</span></summary>' ..
    '<div class="attribution-card" role="note">' .. table.concat(rows, "") .. '</div></details>'
end

local function signature(ids, contributors, uncertain)
  local authors, additions = {table.unpack(ids)}, {table.unpack(contributors)}
  table.sort(authors)
  table.sort(additions)
  return table.concat(authors, ",") .. "|" .. table.concat(additions, ",") .. "|" .. tostring(uncertain)
end

local function contribution(div)
  if not has_class(div, "contribution") then return nil end
  local ids, names = read_people(div.attributes.authors, true)
  local contributor_ids, contributors = read_people(div.attributes.contributors, false)
  local status = div.attributes.status
  if status and status ~= "unverified" then
    fail("Unsupported contribution status '" .. status .. "'.")
  end
  local uncertain = status == "unverified"
  if FORMAT:match("html") then
    pandoc.Div(div.content):walk({Div = function(child)
      if has_class(child, "contribution") then
        fail("Nested .contribution blocks are ambiguous; use adjacent blocks instead.")
      end
    end})
    local key = signature(ids, contributor_ids, uncertain)
    if key ~= previous_signature then
      div.content:insert(1, pandoc.RawBlock("html", attribution_html(ids, names, contributor_ids, contributors, uncertain)))
    end
    previous_signature = key
    div.attributes["data-author-ids"] = table.concat(ids, ",")
    div.attributes["data-contributor-ids"] = table.concat(contributor_ids, ",")
    div.attributes["data-attribution-status"] = status or "confirmed"

    div.attributes.authors = nil
    div.attributes.contributors = nil
    div.attributes.status = nil
    return div
  end
  local result = pandoc.Blocks({pandoc.Para({
    pandoc.Strong({pandoc.Str(english and "Attribution: " or "署名：")}),
    pandoc.Str(label_text(names, contributors, uncertain))
  })})
  result:extend(div.content)
  -- Unwrap to ordinary blocks in GFM/PDF: no widget markup or custom source
  -- syntax should be required to read the exported text.
  return result
end

return {{Meta = read_registry}, {Div = contribution}}
