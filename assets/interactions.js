/* BODA's progressive-enhancement layer.
   Streamlit owns navigation and data actions; this adds small, safe browser-only polish. */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-boda-reveal]").forEach((element, index) => {
    element.style.animationDelay = `${index * 70}ms`;
    element.classList.add("boda-reveal");
  });
  const signal = document.querySelector(".city-signal");
  if (signal) {
    signal.addEventListener("click", () => signal.classList.toggle("city-signal--awake"));
  }
});


/* Cycle through the hero photos embedded locally by app.py (as
   .hero-photo-1 ... .hero-photo-N CSS classes, see build_hero_photo_css
   in app.py), crossfading between them via opacity — no network
   requests, so nothing can be hotlink-blocked.

   IMPORTANT: this script runs inside the isolated iframe that
   components.html() creates for the city-signal widget — .hero lives
   on the *main* page, not in here. So we reach out to window.parent's
   document (same-origin, this is safe) instead of the local `document`.

   .hero only exists on the "Discover Mumbai" page, and this iframe is
   NOT recreated when the user navigates between pages (it's the same
   ui.city_signal() call on every rerun, so Streamlit reuses the same
   iframe). That means a one-shot "poll a few times then give up" check
   breaks as soon as the user visits any other page (e.g. Ask BODA) and
   comes back — .hero is gone, then reappears later, and nothing is
   watching for that. So instead we use a MutationObserver that keeps
   watching indefinitely and re-initializes rotation every time a fresh
   .hero node shows up. */
const HERO_PHOTO_COUNT = 17; // update this if you add/remove files in assets/hero
const HERO_SWAP_MS = 5200;   // how long each photo stays fully visible before crossfading

let heroRotationIntervalId = null;

function getHostDocument() {
  try {
    if (window.parent && window.parent.document) {
      console.log("[BODA hero] reached parent document OK");
      return window.parent.document;
    }
  } catch (e) {
    console.error("[BODA hero] could not access window.parent.document:", e);
  }
  console.warn("[BODA hero] falling back to local (iframe) document — .hero will not be found here");
  return document;
}

function initHero(hostDoc, heroElement) {
  console.log("[BODA hero] found .hero element:", heroElement);
  if (heroElement.dataset.bodaHeroInit) {
    console.log("[BODA hero] already initialized, skipping");
    return;
  }
  heroElement.dataset.bodaHeroInit = "true";

  // A previous .hero node may have left its rotation interval running
  // (e.g. the user navigated away and this is a fresh .hero on return).
  // Stop it so we don't accumulate multiple intervals over time.
  if (heroRotationIntervalId !== null) {
    clearInterval(heroRotationIntervalId);
    heroRotationIntervalId = null;
  }

  if (HERO_PHOTO_COUNT < 1) return;

  const layerA = hostDoc.createElement("div");
  const layerB = hostDoc.createElement("div");
  const overlay = hostDoc.createElement("div");
  layerA.className = "hero-bg-layer";
  layerB.className = "hero-bg-layer";
  overlay.className = "hero-overlay";
  heroElement.prepend(overlay);
  heroElement.prepend(layerB);
  heroElement.prepend(layerA);

  const layers = [layerA, layerB];
  let activeLayer = 0;
  let photoIndex = 0; // 0-based; CSS classes are 1-based

  function showNext() {
    const incoming = layers[activeLayer === 0 ? 1 : 0];
    const outgoing = layers[activeLayer];
    incoming.classList.remove(...Array.from(incoming.classList).filter((c) => c.startsWith("hero-photo-")));
    incoming.classList.add(`hero-photo-${photoIndex + 1}`);
    incoming.classList.add("is-active");
    outgoing.classList.remove("is-active");
    activeLayer = activeLayer === 0 ? 1 : 0;
    photoIndex = (photoIndex + 1) % HERO_PHOTO_COUNT;
  }

  showNext(); // first photo
  console.log("[BODA hero] layers inserted and rotation started");
  if (HERO_PHOTO_COUNT > 1) {
    heroRotationIntervalId = setInterval(showNext, HERO_SWAP_MS);
  }
}

function watchForHero() {
  const hostDoc = getHostDocument();

  // Check immediately in case .hero is already on the page.
  const existing = hostDoc.querySelector(".hero");
  if (existing) initHero(hostDoc, existing);

  // Then keep watching forever — this covers Streamlit re-rendering
  // .hero fresh (new DOM node, no bodaHeroInit flag) every time the
  // user navigates back to the "Discover Mumbai" page.
  const observer = new MutationObserver(() => {
    const heroElement = hostDoc.querySelector(".hero");
    if (heroElement && !heroElement.dataset.bodaHeroInit) {
      initHero(hostDoc, heroElement);
    }
  });

  if (hostDoc.body) {
    observer.observe(hostDoc.body, { childList: true, subtree: true });
  } else {
    // Body not ready yet in the host document — try again shortly.
    setTimeout(watchForHero, 300);
  }
}

document.addEventListener("DOMContentLoaded", watchForHero);