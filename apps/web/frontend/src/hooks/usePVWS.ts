import { type PVUpdate, usePVWSContext } from "@/providers/PVWSContext";
import { useCallback, useEffect, useState } from "react";

interface UsePVWSReturn {
  connected: boolean;
  raw: PVUpdate["raw"];
  error: PVUpdate["error"];
  put: (value: number | string) => boolean;
}

export function usePVWS(pvName: string): UsePVWSReturn {
  const [state, setState] = useState<PVUpdate>({
    raw: null,
    error: null,
  });
  const { connected, subscribe, write } = usePVWSContext();

  useEffect(() => {
    // When WS updates and provider receives {type: "update", ..}, provider calls
    // setState callback with that data
    let unsubscribe = subscribe(pvName, setState);
    // return stmt of useEffect should be a function that cleans up useEffect's effect
    return unsubscribe;
  }, [pvName]); // pvName can be modified if usePVWS hook receives a state holding pv name as arg

  const put = useCallback(
    (newValue: number | string) => write(pvName, newValue),
    [pvName], // pvName can be modified if usePVWS hook receives a state holding pv name as arg
  );

  return {
    connected,
    raw: state.raw,
    error: state.error,
    put,
  };
}
