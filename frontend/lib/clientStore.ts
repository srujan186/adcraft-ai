// Small external stores backed by sessionStorage.
//
// Why not just read sessionStorage in a useEffect and setState? Because that
// trips react-hooks/set-state-in-effect and causes a cascading render. These
// stores plug into useSyncExternalStore instead: the server snapshot is null,
// the client snapshot is a cached string, and nothing calls setState in an
// effect.
//
// getSnapshot must return a referentially stable value, so these cache the raw
// JSON string and callers parse it behind a useMemo.

function safeGet(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    // Private mode / blocked site data.
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value);
  } catch {
    // Non-fatal: the in-memory cache still drives this session's UI.
  }
}

function safeRemove(key: string): void {
  try {
    sessionStorage.removeItem(key);
  } catch {
    // Private mode / blocked site data.
  }
}

function createStore(key: string) {
  const listeners = new Set<() => void>();
  let cache: string | null | undefined; // undefined = not yet read

  return {
    subscribe(cb: () => void) {
      listeners.add(cb);
      return () => {
        listeners.delete(cb);
      };
    },
    /** Client snapshot — stable string reference between writes. */
    getSnapshot(): string | null {
      if (cache === undefined) cache = safeGet(key);
      return cache;
    },
    /** Server snapshot — nothing is available during SSR. */
    getServerSnapshot(): string | null {
      return null;
    },
    write(value: unknown): void {
      cache = JSON.stringify(value);
      safeSet(key, cache);
      listeners.forEach((l) => l());
    },
    /**
     * Forget the value entirely.
     *
     * `sessionStorage.removeItem` on its own is not enough: `cache` is a
     * module-level closure, so a subsequent getSnapshot would keep handing
     * back the old string for the life of the tab.
     */
    clear(): void {
      cache = null;
      safeRemove(key);
      listeners.forEach((l) => l());
    },
  };
}

/** The generated ad handed from /generate to /result. */
export const resultStore = createStore("adcraft_result");

/**
 * The bottom-banner details, edited in the editor's Banner tab.
 *
 * This used to be shared with a separate BottomBanner panel on the result
 * page. That page is now the editor itself, so the second view is gone and
 * the store has a single writer again.
 */
export const bannerStore = createStore("adcraft_banner");

/**
 * The ad's scene list, in order — see SceneSlot.
 *
 * Uploads are downscaled to a JPEG data URL before they land here — a raw
 * photo would blow sessionStorage's quota on its own, and safeSet swallowing
 * that failure would make the override vanish on reload with no explanation.
 */
export const scenesStore = createStore("adcraft_scenes");

export interface SceneOverride {
  /** Data URL (upload) or a Pexels CDN URL. */
  src: string;
  kind: "upload" | "stock";
  /** Pexels requires attribution wherever the photo is shown. */
  credit?: string;
  creditUrl?: string;
}

/**
 * One scene of the ad, in order.
 *
 * This replaced a `Record<index, SceneOverride>`, which could not express a
 * deletion: removing scene 2 left every later override pointing at the wrong
 * scene. A list says what the ad is made of, in order, so add, delete and
 * replace are all just list operations.
 */
export interface SceneSlot {
  /**
   * Where the picture comes from: a data URL (upload), an https URL (a stock
   * photo, or one of the site's own images), or "" meaning "you choose" — the
   * backend fills those from the page's photography.
   */
  src: string;
  kind: "page" | "upload" | "stock" | "auto";
  /** Pexels requires attribution wherever the photo is shown. */
  credit?: string;
  creditUrl?: string;
  /**
   * Which scene of the *current* render this slot shows, so its thumbnail and
   * its seek target survive the list being reordered or shortened. Absent on a
   * slot that no render has produced yet.
   */
  thumbIndex?: number;
}

/** What `scenesStore` holds, stamped with the render it was built against. */
export interface SceneEdit {
  renderId: string;
  slots: SceneSlot[];
}

/**
 * Details for the ad's closing card, edited in the editor's End Card tab.
 *
 * These used to drive a strip drawn over the preview and nothing else. They
 * are now sent to the renderer and composited into the MP4 as its final
 * scene, so they are part of what a re-render produces.
 */
export interface BannerData {
  companyName: string;
  phone: string;
  email: string;
  address: string;
  website: string;
  primaryColor: string;
  accentColor: string;
}


/**
 * Wipe everything the editor holds about the *previous* ad.
 *
 * These stores outlive a single generation — they are keyed by name, not by
 * render. Without this, an image uploaded for one ad reappeared as a scene in
 * the next one, and the bottom banner kept the earlier company's details.
 * Call this the moment a new render is about to be stored.
 */
export function resetEditorState(): void {
  bannerStore.clear();
  scenesStore.clear();
  try {
    sessionStorage.removeItem("adcraft_edits");
  } catch {
    // Nothing reads this back today; clearing it just avoids confusion when
    // someone inspects storage.
  }
}
