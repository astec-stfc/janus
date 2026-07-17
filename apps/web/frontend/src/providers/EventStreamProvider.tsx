import { EVENT_INVALIDATIONS } from "@/config/eventInvalidations";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

const EVENTS_URL = "/v1/events";

/**
 * Opens a single SSE connection for the lifetime of the app and invalidates
 * the appropriate query cache entries when given events arrive.
 */
export function EventStreamProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const es = new EventSource(EVENTS_URL);

    for (const [eventType, queryKeys] of Object.entries(EVENT_INVALIDATIONS)) {
      es.addEventListener(eventType, () => {
        for (const key of queryKeys) {
          void queryClient.invalidateQueries({ queryKey: key });
        }
      });
    }

    return () => es.close();
  }, [queryClient]);

  return <>{children}</>;
}
