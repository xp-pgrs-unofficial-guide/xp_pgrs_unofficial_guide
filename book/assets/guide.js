/* Progressive enhancement: native details works without this script. */
(() => {
  "use strict";
  const instances = [];
  let schedule = () => {};
  const highlight = (instance) => {
    const active = instance.details.open && instance.visible !== false;
    instance.blocks?.forEach((block) => block.classList.toggle("attribution-active", active));
    if (instance.overlay) instance.overlay.hidden = !active;
  };
  document.querySelectorAll("details.paragraph-attribution").forEach((details) => {
    const summary = details.querySelector("summary");
    if (!summary) return;
    const instance = { details, summary, pinned: false, focused: false };
    let restoringFocus = false;
    const close = () => {
      instance.pinned = false;
      details.open = false;
      highlight(instance);
      schedule();
    };
    const open = () => {
      if (instance.visible === false) return;
      instances.forEach((other) => { if (other !== instance && other.details.open) other.close(); });
      details.open = true;
      highlight(instance);
      schedule();
    };
    instance.close = close;
    instances.push(instance);
    summary.addEventListener("click", (event) => {
      event.preventDefault();
      // A second click explicitly closes the card even with the mouse over it.
      if (instance.pinned) close();
      else { instance.pinned = true; open(); }
    });
    details.addEventListener("pointerenter", (event) => {
      if (event.pointerType !== "mouse") return;
      open();
    });
    details.addEventListener("pointerleave", () => {
      if (!instance.pinned && !instance.focused) close();
    });
    details.addEventListener("focusin", () => {
      instance.focused = true;
      if (!restoringFocus) open();
    });
    details.addEventListener("focusout", (event) => {
      if (!details.contains(event.relatedTarget)) {
        instance.focused = false;
        close();
      }
    });
    details.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      close();
      // focus() fires focusin synchronously; it must not reopen the disclosure.
      restoringFocus = true;
      summary.focus();
      restoringFocus = false;
    });
    details.addEventListener("toggle", () => {
      if (!details.open) instance.pinned = false;
      highlight(instance);
      schedule();
    });
  });
  document.addEventListener("pointerdown", (event) => {
    instances.forEach(({ details, close }) => {
      if (!details.contains(event.target)) close();
    });
  });

  // A run may span Quarto sections. Measure its original blocks in document
  // order without wrapping or moving headings (which would break the TOC).
  const runs = new Map();
  document.querySelectorAll(".contribution[data-attribution-run]").forEach((block) => {
    const id = block.getAttribute("data-attribution-run");
    if (!runs.has(id)) runs.set(id, []);
    runs.get(id).push(block);
  });
  const positioned = [];
  runs.forEach((blocks) => {
    const details = blocks[0].querySelector("details.paragraph-attribution");
    const instance = instances.find((entry) => entry.details === details);
    if (instance) { instance.blocks = blocks; positioned.push(instance); }
  });
  const rectFor = (element) => {
    const rect = element.getBoundingClientRect?.();
    return rect && [rect.top, rect.bottom, rect.left, rect.right].every(Number.isFinite) &&
      rect.right > rect.left && rect.bottom > rect.top ? rect : null;
  };
  if (!positioned.length || !window.requestAnimationFrame || !document.body.classList.add ||
    !Number.isFinite(window.innerHeight) || !Number.isFinite(window.innerWidth) ||
    !positioned.every(({ blocks, summary }) => blocks.every(rectFor) && rectFor(summary))) return;

  positioned.forEach((instance) => {
    const overlay = document.createElement("div");
    overlay.className = "attribution-range-highlight";
    overlay.setAttribute("aria-hidden", "true");
    overlay.hidden = true;
    document.body.appendChild(overlay);
    instance.overlay = overlay;
    instance.details.style.visibility = "hidden";
  });
  document.body.classList.add("attribution-enhanced");
  const update = () => {
    const height = window.innerHeight;
    const width = window.innerWidth;
    const inset = width <= 991.98 ? 80 : 24;
    positioned.forEach((instance) => {
      const { details, summary, blocks, overlay } = instance;
      const rects = blocks.map(rectFor);
      if (rects.some((rect) => !rect)) {
        instance.visible = false;
        details.style.visibility = "hidden";
        instance.close();
        return;
      }
      const top = rects[0].top;
      const bottom = rects.at(-1).bottom;
      const left = Math.min(...rects.map((rect) => rect.left));
      const right = Math.max(...rects.map((rect) => rect.right));
      instance.visible = bottom > inset && top < height;
      details.style.visibility = instance.visible ? "visible" : "hidden";
      if (!instance.visible) {
        instance.close();
        return;
      }
      const marker = summary.getBoundingClientRect();
      const markerWidth = marker.width || 40;
      const markerHeight = marker.height || 40;
      const markerTop = Math.min(Math.max(top + 4, inset), Math.max(top + 4, bottom - markerHeight - 4));
      details.style.left = `${Math.max(4, Math.min(right - markerWidth - 6, width - markerWidth - 4))}px`;
      details.style.top = `${markerTop}px`;
      const card = details.querySelector(".attribution-card");
      if (details.open && card) {
        const narrow = width <= 991.98;
        const below = Math.max(40, height - markerTop - (narrow ? markerHeight : 0) - 8);
        const above = Math.max(40, markerTop + (narrow ? 0 : markerHeight) - 8);
        // Prefer the roomier side consistently, so revealing a profile hint
        // cannot flip the icons away from the reader's pointer mid-interaction.
        const showAbove = above > below;
        details.classList.toggle("attribution-card-above", showAbove);
        // Tall cards scroll in the larger available space; flipping alone can
        // otherwise put a multi-author card above the top of a small screen.
        card.style.maxHeight = `${showAbove ? above : below}px`;
      }
      const visibleTop = Math.max(0, top);
      const visibleBottom = Math.min(height, bottom);
      Object.assign(overlay.style, {
        left: `${left}px`, top: `${visibleTop}px`, width: `${right - left}px`,
        height: `${visibleBottom - visibleTop}px`,
        borderTopWidth: top >= 0 ? "2px" : "0px",
        borderBottomWidth: bottom <= height ? "2px" : "0px",
      });
      highlight(instance);
    });
  };
  let queued = false;
  schedule = () => {
    if (queued) return;
    queued = true;
    window.requestAnimationFrame(() => { update(); queued = false; });
  };
  window.addEventListener("scroll", schedule, { passive: true, capture: true });
  window.addEventListener("resize", schedule, { passive: true });
  window.addEventListener("load", schedule);
  // Image and font loads can move a run without changing the viewport size.
  document.addEventListener("load", schedule, true);
  document.fonts?.ready?.then(schedule, () => {});
  document.fonts?.addEventListener?.("loadingdone", schedule);
  if (typeof ResizeObserver === "function") {
    const observer = new ResizeObserver(schedule);
    positioned.forEach(({ blocks, details }) => {
      blocks.forEach((block) => observer.observe(block));
      // Profile hints can expand an open card without moving article content.
      const card = details.querySelector(".attribution-card");
      if (card) observer.observe(card);
    });
  }
  schedule();
})();

/* Match Giscus to Quarto's resolved appearance, including a saved manual choice.
   The widget can be inserted after the page has already selected its theme. */
(() => {
  "use strict";
  const origin = "https://giscus.app";
  const sentThemes = new WeakMap();
  const watchedFrames = new WeakSet();
  const readyFrames = new WeakSet();
  const pendingClients = new Set();
  const preferredScheme = window.matchMedia?.("(prefers-color-scheme: dark)");
  const currentTheme = () => {
    if (document.body.classList.contains("quarto-dark")) return "dark";
    if (document.body.classList.contains("quarto-light")) return "light";
    return preferredScheme?.matches ? "dark" : "light";
  };
  const synchronizeFrame = (frame, force = false) => {
    let address;
    try {
      address = new URL(frame.getAttribute("src") || "", window.location.href);
    } catch {
      return;
    }
    if (address.origin !== origin || !frame.contentWindow) return;
    const theme = currentTheme();
    if (!force && sentThemes.get(frame) === theme) return;
    frame.contentWindow.postMessage({ giscus: { setConfig: { theme } } }, origin);
    sentThemes.set(frame, theme);
  };
  const synchronize = () => {
    pendingClients.forEach((client) => client.setAttribute("data-theme", currentTheme()));
    document.querySelectorAll("iframe.giscus-frame").forEach((frame) => {
      if (!watchedFrames.has(frame)) {
        watchedFrames.add(frame);
        frame.addEventListener("load", () => {
          readyFrames.delete(frame);
          synchronizeFrame(frame, true);
        });
      }
      synchronizeFrame(frame);
    });
  };
  new MutationObserver((mutations) => {
    if (mutations.some((mutation) => mutation.type === "childList" ||
      mutation.target === document.body ||
      mutation.target.matches?.("iframe.giscus-frame"))) synchronize();
  }).observe(document.body, {
    childList: true, subtree: true, attributes: true, attributeFilter: ["class", "src"]
  });
  preferredScheme?.addEventListener("change", synchronize);
  // An iframe's load event can precede Giscus's React message listener. Its
  // first resize message confirms that listener is ready; retry once then,
  // using the latest page theme. Later resizes must not form a message loop.
  window.addEventListener("message", (event) => {
    if (event.origin !== origin) return;
    const height = event.data?.giscus?.resizeHeight;
    if (!Number.isFinite(height) || height <= 0) return;
    document.querySelectorAll("iframe.giscus-frame").forEach((frame) => {
      if (frame.contentWindow !== event.source) return;
      const firstReadyMessage = !readyFrames.has(frame);
      readyFrames.add(frame);
      synchronizeFrame(frame, firstReadyMessage);
    });
  });
  synchronize();
  // Resolve the initial theme before Giscus requests its first stylesheet. A
  // late preferred_color_scheme stylesheet could otherwise overwrite a manual
  // choice even after a successful setConfig message.
  document.querySelectorAll("script.guide-giscus-config").forEach((config) => {
    if (config.getAttribute("data-src") !== `${origin}/client.js`) return;
    const client = document.createElement("script");
    for (const { name, value } of config.attributes) {
      if (name.startsWith("data-") && name !== "data-src") client.setAttribute(name, value);
    }
    client.className = "guide-giscus-client";
    client.src = `${origin}/client.js`;
    client.async = true;
    client.crossOrigin = "anonymous";
    client.setAttribute("data-theme", currentTheme());
    pendingClients.add(client);
    client.addEventListener("load", () => pendingClients.delete(client));
    client.addEventListener("error", () => pendingClients.delete(client));
    config.replaceWith(client);
  });
})();

/* Both translations retain explicit section IDs. Keep deep links when changing
   language, without copying query parameters from the reader's current URL. */
(() => {
  "use strict";
  const links = document.querySelectorAll("a.guide-language-switch");
  const synchronize = () => {
    links.forEach((link) => {
      const target = new URL(link.href, window.location.href);
      target.search = "";
      target.hash = window.location.hash;
      link.href = target.href;
    });
  };
  links.forEach((link) => link.addEventListener("click", synchronize));
  window.addEventListener("hashchange", synchronize);
  synchronize();
})();
