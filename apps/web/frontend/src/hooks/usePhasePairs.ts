import type { Beam } from "@/types";
import { useCallback, useState } from "react";

const DEFAULT_PAIRS: [keyof Beam, keyof Beam][] = [
  ["x", "cpx"],
  ["y", "cpy"],
  ["z", "cpz"],
  ["x", "y"],
];

export function usePhasePairs() {
  const [pairs, setPairs] = useState<[keyof Beam, keyof Beam][]>(() => [...DEFAULT_PAIRS]);

  const handleAddPair = useCallback(
    (pair: [keyof Beam, keyof Beam]) => {
      const isDuplicate = pairs.some(([a, b]) => a === pair[0] && b === pair[1]);
      if (!isDuplicate) setPairs((prev) => [...prev, pair]);
    },
    [pairs],
  );

  const handleRemovePair = useCallback((pair: [keyof Beam, keyof Beam]) => {
    setPairs((prev) => prev.filter(([a, b]) => a !== pair[0] || b !== pair[1]));
  }, []);

  return { pairs, handleAddPair, handleRemovePair };
}
