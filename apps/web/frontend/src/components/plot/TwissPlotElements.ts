import { getCssVariable } from "@/lib/utils";
import {
  isPlottedElementType,
  type PlottedElementType,
} from "@/lib/twissPlot";
import type { PhysicalElement } from "@/types";
import type { Data, Shape } from "plotly.js";

export const X_AXIS_SCHEMATIC = "x2";
export const Y_AXIS_SCHEMATIC = "y2";
export const SCHEMATIC_CENTER_Y = 0.5;
export const TWISS_ELEMENT_HOVER_GROUP = "twiss-element-hover";
const MINIMUM_ELEMENT_WIDTH_RATIO = 0.003;

interface ShapeBounds {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
}

type ShapeBuilder = (bounds: ShapeBounds) => Partial<Shape>;

interface ElementPlotConfig {
  buildShape: ShapeBuilder;
  fillColorVariable: string;
  lineColorVariable: string;
  height: number;
}

const buildRectangle: ShapeBuilder = ({ x0, x1, y0, y1 }) => ({
  type: "rect",
  x0,
  x1,
  y0,
  y1,
});

const buildCircle: ShapeBuilder = ({ x0, x1, y0, y1 }) => ({
  type: "circle",
  x0,
  x1,
  y0,
  y1,
});

const buildTriangle: ShapeBuilder = ({ x0, x1, y0, y1 }) => ({
  type: "path",
  path: [
    `M ${x0},${y0}`, // M == "MOVE (CURSOR) TO" (bottom left of base)
    `L ${x1},${y0}`, // L == "(DRAW) LINE TO" (bottom right of base)
    `L ${(x0 + x1) / 2},${y1}`, // L == "(DRAW) LINE TO" (top of triangle)
    "Z", // Z == "CLOSE THE PATH"
  ].join(" "),
});

const ELEMENT_PLOT_CONFIG: Record<PlottedElementType, ElementPlotConfig> = {
  Quadrupole: {
    buildShape: buildRectangle,
    fillColorVariable: "--quadrupole-fill",
    lineColorVariable: "--quadrupole-line",
    height: 0.32,
  },
  Screen: {
    buildShape: buildCircle,
    fillColorVariable: "--screen-fill",
    lineColorVariable: "--screen-line",
    height: 0.4,
  },
  Dipole: {
    buildShape: buildTriangle,
    fillColorVariable: "--dipole-fill",
    lineColorVariable: "--dipole-line",
    height: 0.32,
  },
  RFCavity: {
    buildShape: buildRectangle,
    fillColorVariable: "--rfcavity-fill",
    lineColorVariable: "--rfcavity-line",
    height: 0.24,
  },
};

const getDisplayBounds = (element: PhysicalElement, beamlineWidth: number) => {
  const physicalWidth = element.end - element.start;
  const displayWidth = Math.max(
    physicalWidth,
    beamlineWidth * MINIMUM_ELEMENT_WIDTH_RATIO,
  );
  const centre = (element.start + element.end) / 2;

  return {
    x0: centre - displayWidth / 2,
    x1: centre + displayWidth / 2,
  };
};

const getElementConfig = (element: PhysicalElement) => {
  if (!isPlottedElementType(element.type)) {
    throw new Error(
      `No plot configuration found for element "${element.name}" of type "${element.type}".`,
    );
  }

  return ELEMENT_PLOT_CONFIG[element.type];
};

const getElementBounds = (
  element: PhysicalElement,
  elementConfig: ElementPlotConfig,
  beamlineWidth: number,
): ShapeBounds => {
  const halfHeight = elementConfig.height / 2;
  // elements with negligible physical width are stretched to 0.3% of beam length
  const displayBounds = getDisplayBounds(element, beamlineWidth);

  return {
    ...displayBounds,
    y0: SCHEMATIC_CENTER_Y - halfHeight,
    y1: SCHEMATIC_CENTER_Y + halfHeight,
  };
};

export const buildElementShapes = (
  elements: PhysicalElement[],
  beamlineWidth: number,
): Array<Partial<Shape>> =>
  elements.map((element) => {
    const elementConfig = getElementConfig(element);
    const bounds = getElementBounds(element, elementConfig, beamlineWidth);

    return {
      ...elementConfig.buildShape(bounds),
      xref: X_AXIS_SCHEMATIC,
      yref: Y_AXIS_SCHEMATIC,
      fillcolor: getCssVariable(elementConfig.fillColorVariable),
      line: {
        color: getCssVariable(elementConfig.lineColorVariable),
        width: 1,
      },
    };
  });

export const buildElementHoverTraces = (
  elements: PhysicalElement[],
  beamlineWidth: number,
): Data[] =>
  elements.map((element) => {
    const elementConfig = getElementConfig(element);
    const { x0, x1, y0, y1 } = getElementBounds(
      element,
      elementConfig,
      beamlineWidth,
    );
    const hoverTrace: Data = {
      type: "scatter",
      mode: "lines",
      name: element.name,
      x: [x0, x1, x1, x0, x0],
      y: [y0, y0, y1, y1, y0],
      fill: "toself", // make filled area hoverable
      fillcolor: "rgba(0,0,0,0)",
      line: { color: "rgba(0,0,0,0)", width: 0 },
      hoveron: "fills",
      hoverinfo: "none", // don't show Plotly's own tooltip - we use our own by reacting to `plotly_hover` event
      legendgroup: TWISS_ELEMENT_HOVER_GROUP, // add identifier to hover-type traces which we can match on.
      text: [element.name, element.type].join("\n"),
      showlegend: false,
      xaxis: X_AXIS_SCHEMATIC,
      yaxis: Y_AXIS_SCHEMATIC,
    };

    return hoverTrace;
  });
