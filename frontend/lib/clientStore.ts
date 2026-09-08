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
 * The bottom-banner details. Shared deliberately: the result-page editor and
 * the full-screen video editor's Banner tab are two views of the SAME data,
 * so editing either one now updates the other instead of silently diverging.
 */
export const bannerStore = createStore("adcraft_banner");

export interface BannerData {
  companyName: string;
  phone: string;
  address: string;
  website: string;
  primaryColor: string;
  accentColor: string;
}
