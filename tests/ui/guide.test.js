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

function harness({ dark = false, className = "quarto-light", frames = [] } = {}) {
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
    querySelectorAll(selector) {
      if (selector === "details.paragraph-attribution") return [details];
      if (selector === "iframe.giscus-frame") return frames;
      if (selector === "a.guide-language-switch") return [link];
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
