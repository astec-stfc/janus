import restframeService from "@/services/restframe";
import type { PhysicalElement } from "@/types";
import { useQuery } from "@tanstack/react-query";


export const restframeQueryKeys = {
  availableElementTypes: () => ["restframe", "availableElementTypes"] as const,
  physicalElements: (include: readonly string[]) =>
    ["restframe", "physicalElements", include] as const,
};

export const useAvailableElementTypesQuery = () =>
  useQuery<string[]>({
    queryKey: restframeQueryKeys.availableElementTypes(),
    queryFn: () => restframeService.getAvailableElementTypes(),
    staleTime: Infinity,
  });

export const usePhysicalElementsQuery = () => {
  const { data: availableElementTypes } =
    useAvailableElementTypesQuery();

  return useQuery<PhysicalElement[]>({
    queryKey: restframeQueryKeys.physicalElements(
      availableElementTypes ?? [],
    ),
    queryFn: () =>
      restframeService.getPhysicalElements(
        availableElementTypes ?? [],
      ),
    enabled: !!availableElementTypes,
    staleTime: Infinity,
  });
};
