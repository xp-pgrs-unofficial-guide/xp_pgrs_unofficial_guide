-- Preserve reference anchors without requiring Quarto syntax in the public GFM.
local function anchor(identifier)
  local safe = identifier:gsub("&", "&amp;"):gsub('"', "&quot;"):gsub("<", "&lt;"):gsub(">", "&gt;")
  return pandoc.RawBlock("html", '<a id="' .. safe .. '"></a>')
end

function Header(header)
  if header.identifier ~= "" then return {anchor(header.identifier), header} end
end

function Div(div)
  if div.identifier ~= "" then
    div.content:insert(1, anchor(div.identifier))
    div.identifier = ""
    return div
  end
end

function Figure(figure)
  -- A plain image is easier for both Markdown readers and agents than a raw
  -- HTML <figure>. Keep explicit captions if they differ from the image alt.
  local blocks = pandoc.Blocks({})
  if figure.identifier ~= "" then blocks:insert(anchor(figure.identifier)) end
  blocks:extend(figure.content)
  local caption = figure.caption and figure.caption.long
  if caption and #caption > 0 and pandoc.utils.stringify(caption) ~= pandoc.utils.stringify(figure.content) then
    blocks:extend(caption)
  end
  return blocks
end
