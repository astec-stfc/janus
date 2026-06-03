import { PVWSContext, type PVUpdate } from "@/providers/PVWSContext";

import PVWS from "@/services/pvws/pvws";
import type { ServerMessage } from "@/types/pvws";
import { useCallback, useEffect, useRef, useState } from "react";

function getPVWSUrl() {
  const configuredUrl = import.meta.env.VITE_PVWS_URL?.trim();
  if (configuredUrl) return configuredUrl;

  const port = import.meta.env.VITE_PVWS_PORT?.trim() || "8080";
  const protocol = "ws";
  return `${protocol}://${window.location.hostname}:${port}/pvws/pv`;
}

export function PVWSProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  // `connectedRef: For internal logic - used inside callbacks/closures without
  //  causing re-renders. Otherwise, must provide `connected` in dependency array
  // of `UseCallback` but still a bad pattern as we'd rather read the value directly
  // instead of triggering the callback to run again and again to update stale closures.
  const connectedRef = useRef(false);
  const pvws = useRef<PVWS | null>(null);
  const subscribersRef = useRef<Map<string, Set<(update: PVUpdate) => void>>>(
    new Map(),
  );
  const pvCacheRef = useRef<Map<string, PVUpdate>>(new Map());

  useEffect(() => {
    const wsUrl = getPVWSUrl();

    const handleConnection = (isConnected: boolean) => {
      connectedRef.current = isConnected;
      setConnected(isConnected);

      if (isConnected && pvws.current) {
        const pvs: string[] = [];
        // Re-mount all PVs that compts were monitoring before a disconnect (e.g. network hiccup)
        for (const [pvName, subs] of subscribersRef.current.entries()) {
          if (subs.size > 0) pvs.push(pvName);
        }
        if (pvs.length > 0) {
          pvws.current.subscribe(pvs);
        }
      }
    };

    const handleMessage = (message: ServerMessage) => {
      if (message.type === "update") {
        const updateMsg = message;
        const callbacks = subscribersRef.current.get(updateMsg.pv);

        // !callbacks: Map has no entry for this PV (never subscribed)
        // callbacks.size === 0: Set exists but empty (all subscribers unsubscribed)
        if (!callbacks || callbacks.size === 0) {
          return;
        }

        // PV update data formatted for components to use
        const incomingUpdate: PVUpdate = {
          raw: updateMsg,
          error: null,
        };
        pvCacheRef.current.set(updateMsg.pv, incomingUpdate);

        for (const cb of callbacks) {
          cb(incomingUpdate);
        }

        return;
      }

      if (message.type === "error") {
        const errorMsg = message;
        if (!errorMsg.pv) {
          return;
        }

        const callbacks = subscribersRef.current.get(errorMsg.pv);
        // !callbacks: Map has no entry for this PV (never subscribed)
        // callbacks.size === 0: Set exists but empty (all subscribers unsubscribed)
        if (!callbacks || callbacks.size === 0) {
          return;
        }

        const prevState = pvCacheRef.current.get(errorMsg.pv) ?? {
          raw: null,
          displayValue: null,
          error: null,
        };
        // PV update data formatted for components to use
        const incomingUpdate: PVUpdate = {
          ...prevState,
          error: errorMsg.message,
        };
        pvCacheRef.current.set(errorMsg.pv, incomingUpdate);

        for (const cb of callbacks) {
          cb(incomingUpdate);
        }
      }
    };

    pvws.current = new PVWS(wsUrl, handleConnection, handleMessage);
    pvws.current.open();

    return () => {
      // cleanup
      pvws.current?.close();
      pvws.current = null;
      subscribersRef.current.clear();
      pvCacheRef.current.clear();
    };
  }, []);

  // Here's our wrapper around the `pvws.subscribe` (which only informs the java server to
  // start tracking the subscribed PVs, but has no responsibility of doing anything
  // when PVs update, besides sending:`{ type: "update", pv: "ca://MY:PV", value: 123 }`.
  // Adding callbacks upon receiving the above data is the job of this wrapper.
  const subscribe = useCallback(
    (pvName: string, cb: (update: PVUpdate) => void) => {
      // Get or create callbacks Set for this PV
      let callbacks = subscribersRef.current.get(pvName);
      if (!callbacks) {
        callbacks = new Set();
        subscribersRef.current.set(pvName, callbacks);
      }

      // Mount server subscription for first subscriber
      const isFirstSubscriber = callbacks.size === 0;
      if (isFirstSubscriber) {
        if (pvws.current && connectedRef.current) {
          pvws.current.subscribe(pvName); // Send "subscribe" message to server
        }
      }

      // Add this callback to the Set (happens for every subscriber)
      callbacks.add(cb);

      // Deliver cached value immediately to new subscriber
      const cachedState = pvCacheRef.current.get(pvName);
      if (cachedState) {
        // Must use microtask to prevent calling setState during render
        // (lets react finish current render before triggering state update)
        queueMicrotask(() => {
          const current = subscribersRef.current.get(pvName);
          if (current?.has(cb)) {
            cb(cachedState);
          }
        });
      }

      function cleanUpSubscription() {
        const current = subscribersRef.current.get(pvName);
        if (!current) return;

        // Remove this callback
        current.delete(cb);

        // Reference counting: Unmount server subscription for last subscriber
        const isLastSubscriber = current.size === 0;
        if (isLastSubscriber) {
          subscribersRef.current.delete(pvName);
          pvCacheRef.current.delete(pvName); // Clear cached PVUpdate

          if (pvws.current) {
            const socket = pvws.current.socket;
            if (connectedRef.current && socket?.readyState === WebSocket.OPEN) {
              pvws.current.clear(pvName); // Send "clear" message to server
            }
          }
        }
      }

      // Subscription pattern: Return cleanup function
      return cleanUpSubscription;
    },
    [],
  );

  const write = useCallback((pvName: string, value: string | number) => {
    if (!pvws.current) return false;

    const socket = pvws.current.socket;
    if (socket?.readyState !== WebSocket.OPEN) return false;

    pvws.current.write(pvName, value);
    return true;
  }, []);

  return (
    <PVWSContext.Provider value={{ connected, subscribe, write }}>
      {children}
    </PVWSContext.Provider>
  );
}
