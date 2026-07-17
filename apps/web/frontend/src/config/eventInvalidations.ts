import type { QueryKey } from "@tanstack/react-query";
import { latticeQueryKeys } from "@/queries/lattice.queries";

/**
 * Maps each Kafka topic name (which becomes the SSE event type) to the list
 * of TanStack Query keys to invalidate when that event is received.
 *
 * To add a new event: add one entry here. 
 */
export const EVENT_INVALIDATIONS: Record<string, QueryKey[]> = {
  lattice_added: [latticeQueryKeys.runUuids()],
};
