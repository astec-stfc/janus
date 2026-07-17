import type { BeamSelectionItem } from "@/hooks/useBeamSelection";
import { getErrorMessage, subtractMean } from "@/lib/utils";
import { useBeamDataQuery, useRunUuidsQuery } from "@/queries/lattice.queries";
import type { Beam } from "@/types";
import { useMemo } from "react";

export function usePlotData(
  selectedUuid: string | null,
  selectedBeam: BeamSelectionItem | null,
  removeZOffset: boolean,
) {
  const runUuidsQuery = useRunUuidsQuery();
  const beamDataQuery = useBeamDataQuery(
    selectedUuid,
    selectedBeam?.kind ?? null,
    selectedBeam?.name ?? null,
  );

  const uuids = runUuidsQuery.data ?? [];
  const beam = beamDataQuery.data ?? null;

  const uuidEmptyText = runUuidsQuery.isLoading
    ? "Loading runs..."
    : runUuidsQuery.isError
      ? `Unable to load runs: ${getErrorMessage(runUuidsQuery.error)}`
      : "No runs found";

  const beamLoadError = beamDataQuery.isError
    ? getErrorMessage(beamDataQuery.error, "Failed to load beam data for the selected item.")
    : null;

  const displayBeam = useMemo<Beam | null>(() => {
    if (!beam) return null;
    if (!removeZOffset || !beam.z) return beam;
    return { ...beam, z: subtractMean(beam.z) };
  }, [beam, removeZOffset]);

  return {
    uuids,
    uuidEmptyText,
    displayBeam,
    beamLoading: beamDataQuery.isLoading,
    beamLoadError,
  };
}
