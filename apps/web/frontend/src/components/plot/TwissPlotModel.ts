import {
  buildElementHoverTraces,
  buildElementShapes,
  SCHEMATIC_CENTER_Y,
  X_AXIS_SCHEMATIC,
  Y_AXIS_SCHEMATIC,
} from "@/components/plot/TwissPlotElements";
import { PLOTTED_TWISS_PARAMETERS } from "@/lib/twissPlot";
import { getCssVariable } from "@/lib/utils";
import type {
  BeamSummaryData,
  BeamSummaryParameter,
  PhysicalElement,
} from "@/types";
import type { Config, Data, Layout } from "plotly.js";

const X_AXIS_TWISS = "x";
const Y_AXIS_TWISS = "y";
const PLOT_TICK_FORMAT = ".3~g";
const TWISS_Y_AXIS_LABEL = "Twiss";
const FULL_WIDTH_DOMAIN: [number, number] = [0, 1];

const GRID_AXIS_SETTINGS = {
  showgrid: true,
  zeroline: false,
};

const BASE_PLOT_LAYOUT: Partial<Layout> = {
  autosize: true,
  margin: { t: 28, l: 64, r: 24, b: 52 },
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { size: 13 },
  showlegend: true,
  legend: { orientation: "h", x: 0, y: 1.1 },
};

export const PLOT_CONFIG: Partial<Config> = {
  responsive: true,
  displaylogo: false,
  scrollZoom: true,
};

interface PlotRange {
  xStart: number;
  xEnd: number;
}

export const getPlotRange = (beamSummaryData: BeamSummaryData): PlotRange => {
  const position = beamSummaryData.xParameter.values;

  return {
    xStart: Math.min(...position),
    xEnd: Math.max(...position),
  };
};

const getAxisStyle = () => ({
  color: getCssVariable("--chart-axis"),
  gridcolor: getCssVariable("--chart-grid-major"),
  linecolor: getCssVariable("--chart-axis"),
});

const buildTwissTraces = (beamSummaryData: BeamSummaryData): Data[] => {
  const traces: Data[] = [];
  const position = beamSummaryData.xParameter;

  for (const selectedTwissParameter of PLOTTED_TWISS_PARAMETERS) {
    const twissParameter = beamSummaryData.yParameters.find(
      (parameter) => parameter.name === selectedTwissParameter.name,
    );
    if (!twissParameter) continue;

    traces.push({
      type: "scatter",
      mode: "lines",
      name: twissParameter.label,
      x: position.values,
      xaxis: X_AXIS_TWISS,
      y: twissParameter.values,
      yaxis: Y_AXIS_TWISS,
      line: { color: selectedTwissParameter.color, width: 3 },
    });
  }

  return traces;
};

const buildBeamLine = (range: PlotRange): Data => ({
  type: "scatter",
  mode: "lines",
  name: "Beamline",
  x: [range.xStart, range.xEnd],
  y: [SCHEMATIC_CENTER_Y, SCHEMATIC_CENTER_Y],
  xaxis: X_AXIS_SCHEMATIC,
  yaxis: Y_AXIS_SCHEMATIC,
  hoverinfo: "skip",
  showlegend: false,
  line: { color: getCssVariable("--beamline-colour"), width: 2 },
});

export const buildPlotData = (
  beamSummaryData: BeamSummaryData,
  elements: PhysicalElement[],
  range: PlotRange,
): Data[] => {
  const upperPlotData = buildTwissTraces(beamSummaryData);
  const lowerPlotData = buildBeamLine(range);
  const hoverTraces = buildElementHoverTraces(
    elements,
    range.xEnd - range.xStart,
  );

  return [...upperPlotData, lowerPlotData, ...hoverTraces];
};

const buildTwissAxisLayout = (): Pick<Layout, "xaxis" | "yaxis"> => ({
  xaxis: {
    domain: FULL_WIDTH_DOMAIN,
    anchor: Y_AXIS_TWISS,
    matches: X_AXIS_SCHEMATIC, // shares same x-axis as lower during interactivity
    showticklabels: false,
    ...getAxisStyle(),
    ...GRID_AXIS_SETTINGS,
  },
  yaxis: {
    domain: [0.3, 1],
    title: { text: TWISS_Y_AXIS_LABEL },
    automargin: true,
    tickformat: PLOT_TICK_FORMAT,
    ...getAxisStyle(),
    ...GRID_AXIS_SETTINGS,
  },
});

const buildSchematicAxisLayout = (
  xParameter: BeamSummaryParameter,
  range: PlotRange,
): Pick<Layout, "xaxis2" | "yaxis2"> => ({
  xaxis2: {
    domain: FULL_WIDTH_DOMAIN,
    anchor: Y_AXIS_SCHEMATIC,
    title: { text: `${xParameter.label} [${xParameter.unit}]` },
    range: [range.xStart, range.xEnd],
    tickformat: PLOT_TICK_FORMAT,
    ...getAxisStyle(),
    ...GRID_AXIS_SETTINGS,
  },
  yaxis2: {
    domain: [0, 0.16],
    range: [0, 1],
    fixedrange: true,
    showticklabels: false,
    showgrid: false,
    zeroline: false,
    ...getAxisStyle(),
  },
});

export const buildPlotLayout = (
  xParameter: BeamSummaryParameter,
  elements: PhysicalElement[],
  range: PlotRange,
): Partial<Layout> => ({
  ...BASE_PLOT_LAYOUT,
  font: { color: getCssVariable("--chart-axis"), size: 13 },
  ...buildTwissAxisLayout(),
  ...buildSchematicAxisLayout(xParameter, range),
  shapes: buildElementShapes(elements, range.xEnd - range.xStart),
});
