import type { BeamSummary, BeamSummaryData, PhysicalElement } from "@/types";

export const TWISS_PLOT_LAYOUT = "CLARA";

export const PLOTTED_ELEMENT_TYPES = [
  "Quadrupole",
  "Screen",
  "Dipole",
  "RFCavity",
] as const;

export type PlottedElementType = (typeof PLOTTED_ELEMENT_TYPES)[number];

export const isPlottedElementType = (
  elementType: string,
): elementType is PlottedElementType =>
  PLOTTED_ELEMENT_TYPES.includes(elementType as PlottedElementType);

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
