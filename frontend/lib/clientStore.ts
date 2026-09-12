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
 * Per-scene image replacements made in the editor, keyed by scene index.
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

export type SceneOverrides = Record<string, SceneOverride>;

export interface BannerData {
  companyName: string;
  phone: string;
  address: string;
  website: string;
  primaryColor: string;
  accentColor: string;
}
