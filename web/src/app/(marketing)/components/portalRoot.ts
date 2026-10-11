/**
 * Portal target for the legacy marketing site. Its stylesheet is scoped under
 * .mk / .mk-p (see legacy.css), so a portal straight onto document.body would
 * render unstyled. Everything portalled goes into this one .mk-p container.
 */
export function portalRoot(): HTMLElement {
  let el = document.getElementById("mk-portal");
  if (!el) {
    el = document.createElement("div");
    el.id = "mk-portal";
    el.className = "mk-p";
    document.body.appendChild(el);
  }
  return el;
}
