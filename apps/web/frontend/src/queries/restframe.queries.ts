import { PLOTTED_ELEMENT_TYPES, TWISS_PLOT_LAYOUT } from "@/lib/twissPlot";
import restframeService from "@/services/restframe";
import type { PhysicalElement } from "@/types";
import { useQuery } from "@tanstack/react-query";

interface PhysicalElementsQueryOptions {
  layout?: string;
  include?: readonly string[];
  enabled?: boolean;
}

export const restframeQueryKeys = {
  physicalElements: (layout: string, include: readonly string[]) =>
    ["restframe", "physicalElements", layout, include] as const,
};

export const usePhysicalElementsQuery = ({
  layout = TWISS_PLOT_LAYOUT,
  include = PLOTTED_ELEMENT_TYPES,
  enabled = true,
}: PhysicalElementsQueryOptions = {}) =>
  useQuery<PhysicalElement[]>({
    queryKey: restframeQueryKeys.physicalElements(layout, include),
    queryFn: () => restframeService.getPhysicalElements(layout, include),
    enabled,
    staleTime: Infinity,
  });
