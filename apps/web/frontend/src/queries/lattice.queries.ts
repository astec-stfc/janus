import latticeGraphqlService from "@/services/lattice.graphql";
import latticeRestService, { type BeamKind } from "@/services/lattice.rest";
import { useQuery } from "@tanstack/react-query";

export type { BeamKind };

const RUN_UUIDS_STALE_TIME_MS = 300_000;
const UUID_SCOPED_GC_TIME_MS = 5 * 60 * 1000;

export const latticeQueryKeys = {
  // `all` is used as the base cache key. If the lattice changes, we can
  // invalidate the entire cache for all chains (since all chains are
  // prefixed with "lattice", e.g.:
  // ["lattice", <uuid>, "screen", <beamName>, "beamData"])
  // But, if we invalidated "runUuids" (["lattice", "runUuids"]), then the
  // above won't be invalidated.

  // Since data for a UUID is treated as immutable and complete, invalidation
  // here is not very useful, but the remaining tanstack features are useful.
  all: ["lattice"] as const,
  runUuids: () => [...latticeQueryKeys.all, "runUuids"] as const,
  byUuid: (uuid: string | null) => [...latticeQueryKeys.all, uuid] as const,
  screens: (uuid: string | null) =>
    [...latticeQueryKeys.byUuid(uuid), "screens"] as const,
  markers: (uuid: string | null) =>
    [...latticeQueryKeys.byUuid(uuid), "markers"] as const,
  beamData: (
    uuid: string | null,
    beamKind: BeamKind | null,
    beamName: string | null,
  ) =>
    [...latticeQueryKeys.byUuid(uuid), beamKind, beamName, "beamData"] as const,
  beamSummary: (uuid: string | null) =>
    [...latticeQueryKeys.byUuid(uuid), "beamSummary"] as const,
};

export const useRunUuidsQuery = () =>
  // useQuery internally subscribes the component it's used in (`Plot`).
  // to the cache key `queryKey`. When any data stored at that
  // cache key: `Query.data`/`Query.isLoading`/`Query.isError` updates,
  // the componenet re-renders.
  useQuery({
    queryKey: latticeQueryKeys.runUuids(), // 2. cache under this key.
    queryFn: latticeGraphqlService.getRunUuids, // 1. fetch uuids to get data
    staleTime: RUN_UUIDS_STALE_TIME_MS,
  });

export const useScreenNamesQuery = (uuid: string | null) =>
  useQuery({
    queryKey: latticeQueryKeys.screens(uuid),
    queryFn: () => latticeGraphqlService.getScreenNames(uuid!),
    enabled: Boolean(uuid),
    staleTime: Infinity,
    gcTime: UUID_SCOPED_GC_TIME_MS,
  });

export const useMarkerNamesQuery = (uuid: string | null) =>
  useQuery({
    queryKey: latticeQueryKeys.markers(uuid),
    queryFn: () => latticeGraphqlService.getMarkerNames(uuid!),
    enabled: Boolean(uuid),
    staleTime: Infinity,
    gcTime: UUID_SCOPED_GC_TIME_MS,
  });

export const useBeamDataQuery = (
  uuid: string | null,
  beamKind: BeamKind | null,
  beamName: string | null,
) =>
  useQuery({
    queryKey: latticeQueryKeys.beamData(uuid, beamKind, beamName),
    queryFn: () => latticeRestService.getBeam(uuid!, beamName!, beamKind!),
    enabled: Boolean(uuid && beamKind && beamName),
    staleTime: Infinity,
    gcTime: UUID_SCOPED_GC_TIME_MS,
  });

export const useBeamSummaryQuery = (uuid: string | null) =>
  useQuery({
    queryKey: latticeQueryKeys.beamSummary(uuid),
    queryFn: () => latticeGraphqlService.getBeamSummary(uuid!),
    enabled: Boolean(uuid),
    staleTime: Infinity,
    gcTime: UUID_SCOPED_GC_TIME_MS,
  });
