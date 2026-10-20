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

function harness({ dark = false, className = "quarto-light", frames = [], configs = [] } = {}) {
  const body = { className, classList: { contains(value) { return body.className.split(/\s+/).includes(value); } } };
  const media = Object.assign(new Events(), { matches: dark });
  const window = Object.assign(new Events(), {
    location: { href: "https://example.test/guide/content/apr.html?private=do-not-forward#sec.IPAP", hash: "#sec.IPAP" },
    matchMedia: () => media,
  });
  const link = Object.assign(new Events(), { href: "https://example.test/guide/en/content/apr.html" });
  const summary = Object.assign(new Events(), { focused: false, focus() { this.focused = true; } });
  const details = Object.assign(new Events(), {
    open: false,
    querySelector: () => summary,
    contains: (node) => node === summary,
  });
  const document = Object.assign(new Events(), {
    body,
    createElement(tag) {
      assert.equal(tag, "script");
      const attributes = new Map();
      return Object.assign(new Events(), {
        setAttribute(name, value) { attributes.set(name, value); },
        getAttribute(name) { return attributes.get(name) ?? null; },
      });
    },
    querySelectorAll(selector) {
      if (selector === "details.paragraph-attribution") return [details];
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
  vm.runInNewContext(script, { document, window, URL, MutationObserver });
  return { body, window, document, media, link, details, summary, frames, observation };
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
