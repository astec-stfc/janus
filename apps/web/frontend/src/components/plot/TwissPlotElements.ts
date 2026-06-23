import { getCssVariable } from "@/lib/utils";
import type { PhysicalElement } from "@/types";
import type { Shape } from "plotly.js";

export const X_AXIS_SCHEMATIC = "x2";
export const Y_AXIS_SCHEMATIC = "y2";
export const SCHEMATIC_CENTER_Y = 0.5;

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

const ELEMENT_PLOT_CONFIG: Record<string, ElementPlotConfig> = {
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

export const PLOTTED_ELEMENT_TYPES = Object.keys(ELEMENT_PLOT_CONFIG);

export const buildElementShapes = (
  elements: PhysicalElement[],
): Array<Partial<Shape>> =>
  elements.map((element) => {
    const elementConfig = ELEMENT_PLOT_CONFIG[element.type];
    if (!elementConfig) {
      throw new Error(
        `No plot configuration found for element "${element.name}" of type "${element.type}".`,
      );
    }

    const halfHeight = elementConfig.height / 2;
    const bounds: ShapeBounds = {
      x0: element.start,
      x1: element.end,
      y0: SCHEMATIC_CENTER_Y - halfHeight,
      y1: SCHEMATIC_CENTER_Y + halfHeight,
    };

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
