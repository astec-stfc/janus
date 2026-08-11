import {
  type BeamKind,
  useMarkerNamesQuery,
  useScreenNamesQuery,
} from "@/queries/lattice.queries";
import { useCallback, useMemo, useState } from "react";

export interface BeamSelectionItem {
  name: string;
  kind: BeamKind;
}

const EMPTY_NAMES: string[] = [];

export function useBeamSelection() {
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null);
  const [selectedBeam, setSelectedBeam] = useState<BeamSelectionItem | null>(
    null,
  );

  const screenNamesQuery = useScreenNamesQuery(selectedUuid);
  const markerNamesQuery = useMarkerNamesQuery(selectedUuid);

  const screenNames = screenNamesQuery.data ?? EMPTY_NAMES;
  const markerNames = markerNamesQuery.data ?? EMPTY_NAMES;

  const namesLoading = screenNamesQuery.isLoading || markerNamesQuery.isLoading;
  const namesLoadError =
    screenNamesQuery.isError || markerNamesQuery.isError
      ? "Failed to load screens and markers."
      : null;

  const beamKindMap = useMemo(() => {
    const map = new Map<string, BeamKind>();
    for (const name of screenNames) map.set(name, "screen");
    for (const name of markerNames) map.set(name, "marker");
    return map;
  }, [screenNames, markerNames]);

  const beamOptions = useMemo(
    () => [
      ...screenNames.map((name) => ({ label: `screen: ${name}`, value: name })),
      ...markerNames.map((name) => ({ label: `marker: ${name}`, value: name })),
    ],
    [screenNames, markerNames],
  );

  const handleUuidSelect = useCallback((uuid: string) => {
    setSelectedUuid(uuid);
  }, []);

  const activeBeam = useMemo(() => {
    if (!selectedBeam) return null;
    if (namesLoading || namesLoadError) return selectedBeam; // use previous screen
    // check name and kind exist for newly selected uuid. If so, re-use previous screen
    return beamKindMap.get(selectedBeam.name) === selectedBeam.kind
      ? selectedBeam
      : null; // otherwise make user pick new screen
  }, [beamKindMap, namesLoadError, namesLoading, selectedBeam]);

  const handleBeamSelection = useCallback(
    (name: string) => {
      const kind = beamKindMap.get(name);
      if (!kind) return;
      setSelectedBeam({ name, kind });
    },
    [beamKindMap],
  );

  return {
    selectedUuid,
    selectedBeam: activeBeam,
    beamOptions,
    namesLoading,
    namesLoadError,
    beamEmptyText: selectedUuid
      ? namesLoading
        ? "Loading screens and markers..."
        : (namesLoadError ?? "No beams found.")
      : "Select a run",
    handleUuidSelect,
    handleBeamSelection,
  };
}
