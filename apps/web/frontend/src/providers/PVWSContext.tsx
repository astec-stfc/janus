import type { UpdateMessage } from "@/types/pvws";
import { createContext, useContext } from "react";

// Data model for each component receives when a PV updates.
export interface PVUpdate {
  raw: UpdateMessage | null;
  error: string | null;
}

export interface PVWSContextValue {
  connected: boolean;
  subscribe: (pvName: string, cb: (update: PVUpdate) => void) => () => void;
  write: (pvName: string, value: string | number) => boolean;
}

export const PVWSContext = createContext<PVWSContextValue | null>(null);

export function usePVWSContext() {
  // `useContext(PVWSContext)` only returns a context with
  // `value` if used in <PVWSContext.Provider value={...}>
  const context = useContext(PVWSContext);
  if (!context) {
    throw new Error("usePVWSContext must be used within PVWSProvider");
  }
  return context;
}
