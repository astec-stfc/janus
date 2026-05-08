import { type PVUpdate, usePVWSContext } from "@/providers/PVWSContext";
import { useCallback, useEffect, useState } from "react";
import { hasPVValue } from "@/components/pv-manager/utils";

interface UsePVWSGetReturn {
  connected: boolean;
  get: () => void;
  requested: boolean;
  raw: PVUpdate["raw"];
  error: PVUpdate["error"];
}

export function usePVWSGet(pvName: string): UsePVWSGetReturn {
  const [state, setState] = useState<PVUpdate>({
    raw: null,
    error: null,
  });
  // to display "Awaiting" status when no longer subscribed; otherwsie would show "connected"
  const [requested, setRequested] = useState(false);
  const { connected, subscribe } = usePVWSContext();

  useEffect(() => {
    setRequested(false);
    setState({ raw: null, error: null });
  }, [pvName]);

  // Gets for WS are weird since pvws only supports monitoring (via `subscribe`) and writing.
  // The workaround here is to `subscribe` whose cb doesn't just `setState(update)` like
  // usePVWS.ts, but also calls `unsubscribe` which is the cleanup function provided by
  // `subscribe` itself! Sort of like a self-destruct button.
  const get = useCallback(() => {
    setRequested(true);
    setState({ raw: null, error: null });

    let unsubscribe = () => {};
    unsubscribe = subscribe(pvName, (update) => {
      setState(update);

      if (update.error) {
        unsubscribe();
        setRequested(false);
        return;
      }

      // When we subscribe a PV for getting, the first message (ack) will be recognised as such
      // by the lack of a value. So, we want to delay unsubscribing until we receive the 2nd message
      // which contains the value.
      if (!hasPVValue(update.raw)) {
        return;
      }

      unsubscribe();
      setRequested(false);
    });
  }, [pvName, subscribe]);

  return {
    connected,
    get,
    requested,
    raw: state.raw,
    error: state.error,
  };
}
