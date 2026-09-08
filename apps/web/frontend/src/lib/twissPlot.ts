import type { BeamSummary, BeamSummaryData, PhysicalElement } from "@/types";
// import { getAvailableElementTypes} from "@/services/restframe";
import { ELEMENT_PLOT_CONFIG } from "@/components/plot/TwissPlotElements";

// Supported element types are those that have a corresponding entry in ELEMENT_PLOT_CONFIG
export type SupportedPlottedElementType = keyof typeof ELEMENT_PLOT_CONFIG;

export const isSupportedElementType = (
  elementType: string,
): elementType is SupportedPlottedElementType =>
  Object.hasOwn(ELEMENT_PLOT_CONFIG, elementType);


export const PLOTTED_TWISS_PARAMETERS = [
  { name: "alpha_x", color: "#002ec4" },
  { name: "alpha_y", color: "#84b1f1" },
  { name: "beta_x", color: "#ff0000" },
  { name: "beta_y", color: "#f69aa9" },
] as const satisfies readonly { name: keyof BeamSummary; color: string }[];

export const PLOTTED_TWISS_PARAMETER_NAMES: readonly (keyof BeamSummary)[] =
  PLOTTED_TWISS_PARAMETERS.map((parameter) => parameter.name);

export interface TwissPlotData {
  beamSummaryData: BeamSummaryData;
  elements: PhysicalElement[];
}
