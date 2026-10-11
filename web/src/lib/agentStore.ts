"use client";

import { useSyncExternalStore } from "react";

let open = false;
let prefill: string | null = null;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export const agentStore = {
  openAgent(question?: string) {
    open = true;
    prefill = question ?? null;
    emit();
  },
  close() {
    open = false;
    emit();
  },
  subscribe(l: () => void) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  getSnapshot() {
    return open;
  },
  takePrefill() {
    const p = prefill;
    prefill = null;
    return p;
  },
};

export function useAgentOpen() {
  return useSyncExternalStore(agentStore.subscribe, agentStore.getSnapshot, () => false);
}
