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
