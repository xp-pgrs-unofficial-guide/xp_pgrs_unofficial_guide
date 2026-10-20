/* Progressive enhancement: native details works without this script. */
(() => {
  "use strict";
  const instances = [];
  document.querySelectorAll("details.paragraph-attribution").forEach((details) => {
    const summary = details.querySelector("summary");
    if (!summary) return;
    let pinned = false;
    const close = () => {
      pinned = false;
      details.open = false;
    };
    instances.push({ details, close });
    summary.addEventListener("click", (event) => {
      event.preventDefault();
      pinned = !pinned;
      // A second click explicitly closes the card even with the mouse over it.
      details.open = pinned;
    });
    details.addEventListener("pointerenter", (event) => {
      if (event.pointerType !== "mouse") return;
      details.open = true;
    });
    details.addEventListener("pointerleave", () => {
      if (!pinned) details.open = false;
    });
    details.addEventListener("focusout", (event) => {
      if (!details.contains(event.relatedTarget)) close();
    });
    details.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      close();
      summary.focus();
    });
  });
  document.addEventListener("pointerdown", (event) => {
    instances.forEach(({ details, close }) => {
      if (!details.contains(event.target)) close();
    });
  });
})();

/* Match Giscus to Quarto's resolved appearance, including a saved manual choice.
   The widget can be inserted after the page has already selected its theme. */
(() => {
  "use strict";
  const origin = "https://giscus.app";
  const sentThemes = new WeakMap();
  const watchedFrames = new WeakSet();
  const readyFrames = new WeakSet();
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
