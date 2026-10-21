"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const script = fs.readFileSync(path.join(__dirname, "../../book/assets/guide.js"), "utf8");

class Events {
  constructor() { this.events = new Map(); }
  addEventListener(type, listener) {
    if (!this.events.has(type)) this.events.set(type, []);
    this.events.get(type).push(listener);
  }
  dispatch(type, fields = {}) {
    const event = { preventDefault() { this.defaultPrevented = true; }, ...fields };
    for (const listener of this.events.get(type) || []) listener(event);
    return event;
  }
}

function classed(element) {
  element.className ||= "";
  element.classList = {
    contains(value) { return element.className.split(/\s+/).includes(value); },
    add(value) { if (!this.contains(value)) element.className = `${element.className} ${value}`.trim(); },
    remove(value) { element.className = element.className.split(/\s+/).filter((entry) => entry !== value).join(" "); },
    toggle(value, force) {
      const active = force ?? !this.contains(value);
      if (active) this.add(value); else this.remove(value);
      return active;
    },
  };
  return element;
}

function attribution(cardHeight = 200) {
  const card = { height: cardHeight, style: {}, getBoundingClientRect() { return { width: 280, height: this.height }; } };
  const details = classed(Object.assign(new Events(), { open: false, style: {} }));
  const summary = Object.assign(new Events(), {
    focused: false,
    focus() { this.focused = true; details.dispatch("focusin", { target: this }); },
    getBoundingClientRect() { return { top: 0, bottom: 40, left: 0, right: 40, width: 40, height: 40 }; },
  });
  Object.assign(details, {
    querySelector(selector) {
      if (selector === "summary") return summary;
      if (selector === ".attribution-card") return card;
      throw new Error(`Unexpected details selector: ${selector}`);
    },
    contains: (node) => node === details || node === summary || node === card,
  });
  return { details, summary, card };
}

function contribution(run, top, bottom, marker = null, parentElement = {}) {
  return classed({
    className: "contribution", parentElement, rect: { top, bottom, left: 100, right: 800 },
    getAttribute: (name) => name === "data-attribution-run" ? run : null,
    querySelector: () => marker?.details || null,
    getBoundingClientRect() { return { ...this.rect, width: this.rect.right - this.rect.left, height: this.rect.bottom - this.rect.top }; },
  });
}

function harness({ dark = false, className = "quarto-light", frames = [], configs = [], blocks = [],
  viewport = null, observeResize = true } = {}) {
  const body = classed({ className, children: [], appendChild(child) { this.children.push(child); } });
  const media = Object.assign(new Events(), { matches: dark });
  const animationFrames = [];
  const window = Object.assign(new Events(), {
    location: { href: "https://example.test/guide/content/apr.html?private=do-not-forward#sec.IPAP", hash: "#sec.IPAP" },
    matchMedia: () => media,
    ...(viewport && { innerWidth: viewport.width, innerHeight: viewport.height,
      requestAnimationFrame(callback) { animationFrames.push(callback); } }),
  });
  const link = Object.assign(new Events(), { href: "https://example.test/guide/en/content/apr.html" });
  const markers = blocks.map((block) => block.querySelector()).filter(Boolean);
  const fallback = attribution();
  const details = markers[0] || fallback.details;
  const summary = details.querySelector("summary");
  const fonts = new Events();
  let fontsReady;
  fonts.ready = { then(callback) { fontsReady = callback; } };
  const document = Object.assign(new Events(), {
    body, fonts,
    createElement(tag) {
      assert.ok(["script", "div"].includes(tag));
      const attributes = new Map();
      return Object.assign(new Events(), {
        style: {},
        setAttribute(name, value) { attributes.set(name, value); },
        getAttribute(name) { return attributes.get(name) ?? null; },
      });
    },
    querySelectorAll(selector) {
      if (selector === "details.paragraph-attribution") return markers.length ? markers : [details];
      if (selector === ".contribution[data-attribution-run]") return blocks;
      if (selector === "iframe.giscus-frame") return frames;
      if (selector === "a.guide-language-switch") return [link];
      if (selector === "script.guide-giscus-config") return configs;
      throw new Error(`Unexpected selector: ${selector}`);
    },
  });
  const observation = {};
  class MutationObserver {
    constructor(callback) { observation.notify = callback; }
    observe(target, options) { observation.target = target; observation.options = options; }
  }
  const resizeObservation = { targets: [] };
  class ResizeObserver {
    constructor(callback) { resizeObservation.notify = callback; }
    observe(target) { resizeObservation.targets.push(target); }
  }
  vm.runInNewContext(script, { document, window, URL, MutationObserver,
    ResizeObserver: observeResize ? ResizeObserver : undefined });
  function flushFrames() {
    let count = 0;
    while (animationFrames.length) {
      assert.ok(count++ < 5, "geometry updates must not create an animation loop");
      for (const callback of animationFrames.splice(0)) callback();
    }
    return count;
  }
  return { body, window, document, media, link, details, summary, frames, observation,
    resizeObservation, flushFrames, animationFrames, fontsReady: () => fontsReady?.() };
}

function giscusConfig(overrides = {}) {
  const fields = {
    "data-src": "https://giscus.app/client.js", "data-repo": "example/guide",
    "data-repo-id": "repo-id", "data-category-id": "category-id",
    "data-mapping": "specific", "data-term": "xp-guide-apr", "data-strict": "1",
    "data-lang": "zh-CN", "data-theme": "preferred_color_scheme", "data-loading": "lazy",
    ...overrides,
  };
  return {
    fields, attributes: Object.entries(fields).map(([name, value]) => ({ name, value })),
    getAttribute: (name) => fields[name] ?? null,
    replaceWith(client) { assert.equal(this.client, undefined); this.client = client; },
  };
}

test("Giscus starts with the saved page theme instead of requesting the system stylesheet", () => {
  for (const [dark, className, expected] of [[true, "quarto-light", "light"], [false, "quarto-dark", "dark"]]) {
    for (const language of ["zh-CN", "en"]) {
      const config = giscusConfig({ "data-lang": language });
      harness({ dark, className, configs: [config] });
      const client = config.client;
      assert.equal(client.src, "https://giscus.app/client.js");
      assert.equal(client.getAttribute("data-theme"), expected);
      for (const [name, value] of Object.entries(config.fields)) {
        if (!["data-src", "data-theme"].includes(name)) assert.equal(client.getAttribute(name), value);
      }
      assert.equal(client.getAttribute("data-src"), null);
      assert.equal(client.async, true);
      assert.equal(client.crossOrigin, "anonymous");
    }
  }
});

test("a theme changed while the client downloads is used when Giscus first executes", () => {
  const config = giscusConfig();
  const h = harness({ configs: [config] });
  h.body.className = "quarto-dark";
  h.observation.notify([{ type: "attributes", target: h.body }]);
  assert.equal(config.client.getAttribute("data-theme"), "dark");
  config.client.dispatch("load");
  const frame = widget();
  h.frames.push(frame);
  h.observation.notify([{ type: "childList", target: h.body }]);
  ready(h, frame);
  h.body.className = "quarto-light";
  h.observation.notify([{ type: "attributes", target: h.body }]);
  assert.equal(theme(frame), "light");
  assert.equal(frame.src, "https://giscus.app/en/widget");
  assert.equal(config.client.getAttribute("data-theme"), "dark");
});

test("Giscus configuration cannot load a client from another origin", () => {
  const config = giscusConfig({ "data-src": "https://giscus.app.attacker.test/client.js" });
  harness({ configs: [config] });
  assert.equal(config.client, undefined);
});

function widget(src = "https://giscus.app/en/widget") {
  const messages = [];
  return Object.assign(new Events(), {
    src, messages,
    matches: (selector) => selector === "iframe.giscus-frame",
    getAttribute(name) { return name === "src" ? this.src : null; },
    contentWindow: { postMessage(message, origin) { messages.push({ message, origin }); } },
  });
}
function theme(frame) { return frame.messages.at(-1).message.giscus.setConfig.theme; }
function ready(h, frame, height = 500) {
  h.window.dispatch("message", {
    origin: "https://giscus.app", source: frame.contentWindow,
    data: { giscus: { resizeHeight: height } },
  });
}

test("saved light choice takes precedence over a dark operating system", () => {
  const frame = widget();
  harness({ dark: true, className: "quarto-light", frames: [frame] });
  assert.equal(theme(frame), "light");
  assert.equal(frame.messages[0].origin, "https://giscus.app");
});

test("a late widget and its load event receive the current Quarto theme", () => {
  const h = harness({ className: "quarto-dark" });
  const frame = widget();
  h.frames.push(frame);
  h.observation.notify([{ type: "childList", target: h.body }]);
  assert.equal(theme(frame), "dark");
  frame.dispatch("load");
  assert.equal(frame.messages.length, 2);
  assert.equal(theme(frame), "dark");
});

test("theme changes propagate once; unrelated DOM changes do not resend", () => {
  const frame = widget();
  const h = harness({ frames: [frame] });
  h.body.className = "quarto-dark";
  h.observation.notify([{ type: "attributes", target: h.body, attributeName: "class" }]);
  assert.equal(theme(frame), "dark");
  assert.equal(frame.messages.length, 2);
  for (let i = 0; i < 5; i++) h.observation.notify([{ type: "childList", target: h.body }]);
  assert.equal(frame.messages.length, 2);
});

test("messages are never sent to an iframe at another origin", () => {
  const malicious = widget("https://giscus.app.attacker.test/widget");
  const blank = widget("about:blank");
  const h = harness({ frames: [malicious, blank] });
  malicious.dispatch("load");
  assert.equal(malicious.messages.length, 0);
  assert.equal(blank.messages.length, 0);
  blank.src = "https://giscus.app/zh-CN/widget";
  h.observation.notify([{ type: "attributes", target: blank, attributeName: "src" }]);
  assert.equal(theme(blank), "light");
});

test("system preference is used before Quarto has selected a class", () => {
  const frame = widget();
  const h = harness({ dark: true, className: "", frames: [frame] });
  assert.equal(theme(frame), "dark");
  h.media.matches = false;
  h.media.dispatch("change");
  assert.equal(theme(frame), "light");
});

test("a widget that drops messages before hydration receives the latest theme when ready", () => {
  const frame = widget();
  let receiverReady = false;
  const delivered = [];
  frame.contentWindow.postMessage = (message, origin) => {
    if (receiverReady) delivered.push({ message, origin });
  };
  const h = harness({ dark: true, className: "quarto-light", frames: [frame] });
  frame.dispatch("load");
  assert.equal(delivered.length, 0);
  receiverReady = true;
  ready(h, frame);
  assert.equal(delivered.length, 1);
  assert.equal(delivered[0].message.giscus.setConfig.theme, "light");
  assert.equal(delivered[0].origin, "https://giscus.app");
});

test("readiness uses a theme changed during loading and resizes do not create a message loop", () => {
  const frame = widget();
  const h = harness({ frames: [frame] });
  h.body.className = "quarto-dark";
  h.observation.notify([{ type: "attributes", target: h.body }]);
  const beforeReady = frame.messages.length;
  ready(h, frame);
  assert.equal(frame.messages.length, beforeReady + 1);
  assert.equal(theme(frame), "dark");
  for (let i = 0; i < 10; i++) ready(h, frame, 500 + i);
  assert.equal(frame.messages.length, beforeReady + 1);
  h.body.className = "quarto-light";
  h.observation.notify([{ type: "attributes", target: h.body }]);
  assert.equal(theme(frame), "light");
  const afterSwitch = frame.messages.length;
  ready(h, frame);
  assert.equal(frame.messages.length, afterSwitch);
  frame.dispatch("load");
  const afterReload = frame.messages.length;
  ready(h, frame);
  assert.equal(frame.messages.length, afterReload + 1);
  assert.equal(theme(frame), "light");
});

test("readiness must come from the matching Giscus window and contain a valid height", () => {
  const frame = widget();
  const other = widget();
  const h = harness({ frames: [frame, other] });
  const event = { origin: "https://giscus.app", source: frame.contentWindow,
    data: { giscus: { resizeHeight: 500 } } };
  for (const fields of [
    { origin: "https://giscus.app.attacker.test" },
    { source: {} }, { source: null }, { data: null }, { data: "not a Giscus message" },
    ...[undefined, "500", 0, -1, NaN, Infinity].map((height) => ({ data: { giscus: { resizeHeight: height } } })),
  ]) h.window.dispatch("message", { ...event, ...fields });
  assert.equal(frame.messages.length, 1);
  assert.equal(other.messages.length, 1);
  ready(h, frame);
  assert.equal(frame.messages.length, 2);
  assert.equal(other.messages.length, 1);
});

test("language switching preserves the latest anchor and drops query parameters", () => {
  const h = harness();
  let target = new URL(h.link.href);
  assert.equal(target.pathname, "/guide/en/content/apr.html");
  assert.equal(target.hash, "#sec.IPAP");
  assert.equal(target.search, "");
  h.window.location.hash = "#xp-guide-apr";
  h.window.dispatch("hashchange");
  assert.equal(new URL(h.link.href).hash, "#xp-guide-apr");
  h.window.location.hash = "";
  h.link.dispatch("click");
  assert.equal(new URL(h.link.href).hash, "");
});

test("attribution remains usable with mouse pinning, keyboard and outside clicks", () => {
  const h = harness();
  assert.equal(h.body.classList.contains("attribution-enhanced"), false);
  h.details.dispatch("pointerenter", { pointerType: "mouse" });
  assert.equal(h.details.open, true);
  h.summary.dispatch("click");
  h.details.dispatch("pointerleave");
  assert.equal(h.details.open, true);
  h.details.dispatch("keydown", { key: "Escape" });
  assert.equal(h.details.open, false);
  assert.equal(h.summary.focused, true);
  h.summary.dispatch("click");
  h.document.dispatch("pointerdown", { target: {} });
  assert.equal(h.details.open, false);
  h.details.dispatch("pointerenter", { pointerType: "touch" });
  assert.equal(h.details.open, false);
});

test("an author run follows scrolling across different Quarto sections without moving content", () => {
  const marker = attribution();
  const sections = [{ id: "first-section" }, { id: "next-section" }];
  const blocks = [contribution("1", 100, 200, marker, sections[0]),
    contribution("1", 250, 400, null, sections[0]), contribution("1", 450, 700, null, sections[1])];
  const h = harness({ blocks, viewport: { width: 1200, height: 600 } });
  h.flushFrames();
  assert.equal(h.body.classList.contains("attribution-enhanced"), true);
  assert.equal(marker.details.style.top, "104px");
  assert.equal(marker.details.style.left, "754px");
  marker.details.dispatch("pointerenter", { pointerType: "mouse" });
  h.flushFrames();
  const overlay = h.body.children[0];
  assert.equal(overlay.className, "attribution-range-highlight");
  assert.equal(overlay.getAttribute("aria-hidden"), "true");
  assert.equal(overlay.hidden, false);
  assert.deepEqual([overlay.style.top, overlay.style.height, overlay.style.borderTopWidth,
    overlay.style.borderBottomWidth], ["100px", "500px", "2px", "0px"]);
  blocks.forEach((block) => assert.equal(block.classList.contains("attribution-active"), true));
  blocks.forEach((block) => { block.rect.top -= 300; block.rect.bottom -= 300; });
  h.window.dispatch("scroll");
  h.flushFrames();
  assert.equal(marker.details.style.top, "24px");
  assert.deepEqual([overlay.style.top, overlay.style.height, overlay.style.borderTopWidth,
    overlay.style.borderBottomWidth], ["0px", "400px", "0px", "2px"]);
  assert.equal(blocks[0].parentElement, sections[0]);
  assert.equal(blocks[2].parentElement, sections[1]);
});

test("the marker stops at its true author boundary and closes before the next author", () => {
  const first = attribution();
  const second = attribution();
  const a = contribution("1", -200, 64, first);
  const b = contribution("2", 90, 500, second);
  const h = harness({ blocks: [a, b], viewport: { width: 1200, height: 600 } });
  h.flushFrames();
  assert.equal(first.details.style.top, "20px", "marker is bounded by the last block, even above its sticky inset");
  first.summary.dispatch("click");
  h.flushFrames();
  assert.equal(first.details.open, true);
  a.rect.bottom = 20;
  b.rect.top = 30;
  h.window.dispatch("scroll");
  h.flushFrames();
  assert.equal(first.details.style.visibility, "hidden");
  assert.equal(first.details.open, false);
  assert.equal(a.classList.contains("attribution-active"), false);
  assert.equal(h.body.children[0].hidden, true);
  assert.equal(second.details.style.visibility, "visible");
  assert.equal(second.details.style.top, "34px");
  assert.equal(second.details.open, false);
  a.rect.top = 100;
  a.rect.bottom = 200;
  h.window.dispatch("scroll");
  h.flushFrames();
  first.summary.dispatch("click");
  assert.equal(first.details.open, true, "returning to the run starts with an unpinned, closed card");
});

test("keyboard focus opens the scope; Escape and a second pinned click dismiss it", () => {
  const marker = attribution();
  const block = contribution("1", 100, 500, marker);
  const h = harness({ blocks: [block], viewport: { width: 1200, height: 600 } });
  h.flushFrames();
  marker.details.dispatch("focusin", { target: marker.summary });
  assert.equal(marker.details.open, true);
  assert.equal(block.classList.contains("attribution-active"), true);
  marker.details.dispatch("keydown", { key: "Escape" });
  assert.equal(marker.summary.focused, true);
  assert.equal(marker.details.open, false, "Escape focus restoration must not immediately reopen the card");
  assert.equal(block.classList.contains("attribution-active"), false);
  marker.details.dispatch("focusout", { relatedTarget: {} });
  marker.details.dispatch("focusin", { target: marker.summary });
  marker.summary.dispatch("click");
  marker.details.dispatch("pointerleave");
  assert.equal(marker.details.open, true);
  marker.summary.dispatch("click");
  assert.equal(marker.details.open, false, "the second click wins over focus and hover");
  assert.equal(block.classList.contains("attribution-active"), false);
  assert.equal(h.body.children[0].hidden, true);
  marker.details.dispatch("pointerenter", { pointerType: "touch" });
  assert.equal(marker.details.open, false);
  marker.summary.dispatch("click");
  assert.equal(marker.details.open, true);
  h.document.dispatch("pointerdown", { target: {} });
  assert.equal(marker.details.open, false);
});

test("narrow screens use the navigation inset and cards flip above near the viewport bottom", () => {
  const marker = attribution(220);
  const block = contribution("1", 0, 1000, marker);
  Object.assign(block.rect, { left: 16, right: 374 });
  const h = harness({ blocks: [block], viewport: { width: 390, height: 480 } });
  h.flushFrames();
  assert.equal(marker.details.style.top, "80px");
  assert.equal(marker.details.style.left, "328px");
  marker.summary.dispatch("click");
  h.flushFrames();
  assert.equal(marker.details.classList.contains("attribution-card-above"), false);
  block.rect.top = 300;
  h.window.dispatch("scroll");
  h.flushFrames();
  assert.equal(marker.details.style.top, "304px");
  assert.equal(marker.details.classList.contains("attribution-card-above"), true);
  h.window.innerWidth = 1200;
  h.window.innerHeight = 600;
  block.rect.top = 400;
  h.window.dispatch("resize");
  h.flushFrames();
  assert.equal(marker.details.classList.contains("attribution-card-above"), true);
});

test("expanding profile hints use the larger viewport space and keep tall cards scrollable", () => {
  const marker = attribution(180);
  const block = contribution("1", 200, 1000, marker);
  const h = harness({ blocks: [block], viewport: { width: 390, height: 480 } });
  h.flushFrames();
  marker.summary.dispatch("click");
  h.flushFrames();
  assert.equal(marker.details.classList.contains("attribution-card-above"), false);
  assert.equal(marker.card.style.maxHeight, "228px");
  marker.card.height = 300;
  h.resizeObservation.notify([]);
  h.flushFrames();
  assert.equal(marker.details.classList.contains("attribution-card-above"), false,
               "a card larger than either side must stay in the larger lower space");
  assert.equal(marker.card.style.maxHeight, "228px");
  block.rect.top = 300;
  h.window.dispatch("scroll");
  h.flushFrames();
  assert.equal(marker.details.classList.contains("attribution-card-above"), true);
  assert.equal(marker.card.style.maxHeight, "296px");
  marker.card.height = 100;
  h.resizeObservation.notify([]);
  h.flushFrames();
  assert.equal(marker.details.classList.contains("attribution-card-above"), true,
               "hiding a hint must not move icons away from the pointer");
  assert.equal(marker.card.style.maxHeight, "296px");
});

test("layout changes coalesce into one frame and observe content rather than moving overlays", () => {
  for (const observeResize of [true, false]) {
    const marker = attribution();
    const block = contribution("1", 100, 500, marker);
    const h = harness({ blocks: [block], viewport: { width: 1200, height: 600 }, observeResize });
    h.flushFrames();
    assert.deepEqual(h.resizeObservation.targets, observeResize ? [block, marker.card] : []);
    block.rect.top = 160;
    block.rect.right = 900;
    h.window.dispatch("scroll");
    h.window.dispatch("resize");
    h.window.dispatch("load");
    h.document.dispatch("load", { target: { tagName: "IMG" } });
    h.document.fonts.dispatch("loadingdone");
    h.fontsReady();
    h.resizeObservation.notify?.([]);
    assert.equal(h.animationFrames.length, 1);
    assert.equal(h.flushFrames(), 1);
    assert.equal(marker.details.style.top, "164px");
    assert.equal(marker.details.style.left, "854px");
    assert.equal(h.animationFrames.length, 0);
  }
});
