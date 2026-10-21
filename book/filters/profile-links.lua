-- Shared public-profile link rendering for author pages and attribution cards.
-- Keep one list of supported fields, accessible labels and official icon assets.
local function value(v) return v and pandoc.utils.stringify(v) or "" end
-- Local assets are embedded in HTML so profiles also work below /en/ and when
-- their source is rendered independently of the book project.
local filter_file = debug.getinfo(1, "S").source:gsub("^@", "")
local icon_directory = pandoc.path.normalize(pandoc.path.join({pandoc.path.directory(filter_file), "../assets/icons"}))
local icon_cache = {}
local function read_icon(name)
  if icon_cache[name] then return table.unpack(icon_cache[name]) end
  for _, extension in ipairs({"svg", "png"}) do
    local file = io.open(icon_directory .. "/" .. name .. "." .. extension, "rb")
    if file then
      local contents = file:read("*a")
      file:close()
      icon_cache[name] = {contents, extension}
      return contents, extension
    end
  end
  error("[authors] Missing local profile icon " .. name)
end
local function base64(contents)
  local alphabet, encoded = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/", {}
  for offset = 1, #contents, 3 do
    local first, second, third = contents:byte(offset, offset + 2)
    local bits = first * 65536 + (second or 0) * 256 + (third or 0)
    for _, shift in ipairs({18, 12, 6, 0}) do
      local position = math.floor(bits / 2 ^ shift) % 64 + 1
      encoded[#encoded + 1] = ((shift == 6 and not second) or (shift == 0 and not third))
        and "=" or alphabet:sub(position, position)
    end
  end
  return table.concat(encoded)
end
local module = {}
function module.new(meta, scope)
  scope = scope or ""
  local english = value(meta.lang):match("^en") ~= nil
  local names = (english and meta["guide-authors-en"]) or meta["guide-authors"] or {}
  local profiles = meta["guide-author-profiles"] or {}
  local function profile_links(id)
    local profile, links = profiles[id] or {}, {}
    local orcid = value(profile.orcid)
    if orcid ~= "" then links[#links + 1] = {kind="orcid", label="ORCID", target="https://orcid.org/" .. orcid, identifier=orcid} end
    for _, field in ipairs({
      {"google-scholar", "Google Scholar", "Google Scholar", "google-scholar"},
      {"institutional-profile", "机构主页", "Institutional profile", "institution"},
      {"website", "个人主页", "Website", "website"},
      {"github", "GitHub", "GitHub", "github"},
    }) do
      local target = value(profile[field[1]])
      if target ~= "" then links[#links + 1] = {kind=field[4], label=field[english and 3 or 2], target=target} end
    end
    local email = value(profile.email)
    if email ~= "" then
      links[#links + 1] = {kind="email", label=english and "Email" or "邮箱", target="mailto:" .. email,
        identifier=email, separator=english and ": " or "：", contact=true}
    end
    return links
  end
  local icon_instance = 0
  local function icon_image(name, variant)
    local contents, extension = read_icon(name)
    local classes = "guide-profile-icon-image" .. (variant and (" guide-profile-icon-" .. variant) or "")
    if extension == "png" then
      return '<img class="' .. classes .. '" src="data:image/png;base64,' .. base64(contents) ..
        '" width="24" height="24" alt="" aria-hidden="true" draggable="false">'
    end
    local svg = contents:match("<svg[%s>].-</svg>")
    if not svg then error("[authors] Invalid SVG profile icon " .. name) end
    icon_instance = icon_instance + 1
    local prefix = "guide-profile-icon-" .. (scope ~= "" and (scope .. "-") or "") .. icon_instance .. "-"
    -- Official logo files can contain clipping paths. Give every copy unique
    -- IDs while preserving the supplied shapes, colours and proportions.
    local ids = {}
    for identifier in svg:gmatch('id="([^"]+)"') do ids[identifier] = prefix .. identifier end
    svg = svg:gsub('id="([^"]+)"', function(identifier) return 'id="' .. ids[identifier] .. '"' end)
      :gsub('url%(#([^)]+)%)', function(identifier) return "url(#" .. (ids[identifier] or identifier) .. ")" end)
      :gsub('href="#([^"]+)"', function(identifier) return 'href="#' .. (ids[identifier] or identifier) .. '"' end)
    -- ORCID's supplied SVG has internal .st0/.st1 rules. Scope those class
    -- selectors too, so an inline logo cannot recolour another page figure.
    local classes_by_name = {}
    for names_in_attribute in svg:gmatch('class="([^"]+)"') do
      for name_in_attribute in names_in_attribute:gmatch("%S+") do
        classes_by_name[name_in_attribute] = prefix .. name_in_attribute
      end
    end
    svg = svg:gsub('class="([^"]+)"', function(names_in_attribute)
      return 'class="' .. names_in_attribute:gsub("%S+", classes_by_name) .. '"'
    end)
    for original, scoped in pairs(classes_by_name) do
      local pattern = original:gsub("([^%w])", "%%%1")
      svg = svg:gsub("%." .. pattern .. "%f[^%w_-]", "." .. scoped)
    end
    svg = svg:gsub("<svg", '<svg class="' .. classes .. '" aria-hidden="true" focusable="false"', 1)
    return svg
  end
  local function icon_links(links, id, compact, extra_class)
    local inlines = pandoc.Inlines({})
    local flow_hint = extra_class == "guide-profile-links-attribution"
    for _, link in ipairs(links) do
      local detail = link.label .. (link.separator or ": ") .. (link.identifier or link.target)
      local label = value(names[id]) .. " — " .. detail
      local icon = icon_image(link.kind, link.kind == "github" and "light" or nil)
      if link.kind == "github" then icon = icon .. icon_image("github-dark", "dark") end
      local hint = pandoc.Span({pandoc.Str(detail)}, pandoc.Attr("", {"guide-profile-tooltip"}, {["aria-hidden"]="true"}))
      local content = pandoc.Inlines({
        pandoc.RawInline("html", '<span class="guide-profile-icon" aria-hidden="true">' .. icon .. '</span>'),
      })
      if not flow_hint then content:insert(hint) end
      content:insert(pandoc.Span({pandoc.Str(detail)}, pandoc.Attr("", {"guide-profile-print-label"}, {["aria-hidden"]="true"})))
      inlines:insert(pandoc.Link(content, link.target, "", pandoc.Attr("", {"guide-profile-link"}, {
        title=label, ["aria-label"]=label, ["data-profile-kind"]=link.kind,
      })))
      -- Cards scroll within the viewport. Keep their hints in normal flow so
      -- the hint cannot be clipped by the card's overflow boundary.
      if flow_hint then inlines:insert(hint) end
    end
    local classes = {"guide-profile-links", compact and "guide-profile-links-compact" or "guide-profile-links-profile"}
    if extra_class then classes[#classes + 1] = extra_class end
    return pandoc.Span(inlines, pandoc.Attr("", classes, {
        role="group", ["aria-label"]=english and "Public profile links" or "公开资料链接",
      }))
  end
  return {
    links = profile_links,
    icons = icon_links,
    html = function(links, id, compact, extra_class)
      return pandoc.write(pandoc.Pandoc({pandoc.Plain({icon_links(links, id, compact, extra_class)})}), "html5"):gsub("%s+$", "")
    end,
  }
end
return module
