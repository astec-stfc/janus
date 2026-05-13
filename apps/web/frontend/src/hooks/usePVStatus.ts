import { useMemo } from "react";

import type { UpdateMessage } from "@/types/pvws";

import type { PVStatus } from "@/types";
import { hasPVValue } from "../components/pv-manager/utils";

export function usePVStatus({
  connected,
  error,
  raw,
  active,
}: {
  connected: boolean;
  error: string | null;
  raw: UpdateMessage | null;
  active: boolean;
}): PVStatus {
  const hasValue = useMemo(() => hasPVValue(raw), [raw?.value]);

  if (!connected) return "disconnected";
  if (error) return "disconnected";
  if (!active) return "awaiting";
  // If we received an update but it has no value, the PV is invalid/doesn't exist
  if (raw && !hasValue) return "invalid";
  if (!hasValue) return "awaiting";
  return "connected";
}
