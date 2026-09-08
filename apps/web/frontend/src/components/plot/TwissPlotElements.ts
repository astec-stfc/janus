import { getCssVariable } from "@/lib/utils";
import { isSupportedElementType} from "@/lib/twissPlot";
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

const buildDiamond: ShapeBuilder = ({ x0, x1, y0, y1 }) => ({
  type: "path",
  path: [
    `M ${(x0 + x1) / 2},${y1}`,
    `L ${x1},${(y0 + y1) / 2}`,
    `L ${(x0 + x1) / 2},${y0}`,
    `L ${x0},${(y0 + y1) / 2}`,
    "Z",
  ].join(" "),
});

const buildHexagon: ShapeBuilder = ({ x0, x1, y0, y1 }) => {
  const dx = (x1 - x0) * 0.2;

  return {
    type: "path",
    path: [
      `M ${x0 + dx},${y1}`,
      `L ${x1 - dx},${y1}`,
      `L ${x1},${(y0 + y1) / 2}`,
      `L ${x1 - dx},${y0}`,
      `L ${x0 + dx},${y0}`,
      `L ${x0},${(y0 + y1) / 2}`,
      "Z",
    ].join(" "),
  };
};

const buildHourglass: ShapeBuilder = ({ x0, x1, y0, y1 }) => ({
  type: "path",
  path: [
    `M ${x0},${y1}`,
    `L ${x1},${y0}`,
    `L ${x1},${y1}`,
    `L ${x0},${y0}`,
    "Z",
  ].join(" "),
});

const buildTrapezoid: ShapeBuilder = ({ x0, x1, y0, y1 }) => {
  const inset = (x1 - x0) * 0.2;

  return {
    type: "path",
    path: [
      `M ${x0 + inset},${y1}`,
      `L ${x1 - inset},${y1}`,
      `L ${x1},${y0}`,
      `L ${x0},${y0}`,
      "Z",
    ].join(" "),
  };
};

const buildDoubleTriangle: ShapeBuilder = ({ x0, x1, y0, y1 }) => {
  const mid = (x0 + x1) / 2;

  return {
    type: "path",
    path: [
      `M ${x0},${(y0 + y1) / 2}`,
      `L ${mid},${y1}`,
      `L ${mid},${y0}`,
      "Z",
      `M ${x1},${(y0 + y1) / 2}`,
      `L ${mid},${y1}`,
      `L ${mid},${y0}`,
      "Z",
    ].join(" "),
  };
};

const buildCross: ShapeBuilder = ({ x0, x1, y0, y1 }) => {
  const width = (x1 - x0) * 0.25;
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;

  return {
    type: "path",
    path: [
      `M ${cx - width},${cy}`,
      `L ${cx + width},${cy}`,
      `M ${cx},${y0}`,
      `L ${cx},${y1}`,
    ].join(" "),
  };
};

const buildCapsule: ShapeBuilder = ({ x0, x1, y0, y1 }) => ({
  type: "path",
  path: `
    M ${x0 + (y1 - y0) / 2},${y1}
    L ${x1 - (y1 - y0) / 2},${y1}
    A ${(y1 - y0) / 2},${(y1 - y0) / 2} 0 0 1 ${x1 - (y1 - y0) / 2},${y0}
    L ${x0 + (y1 - y0) / 2},${y0}
    A ${(y1 - y0) / 2},${(y1 - y0) / 2} 0 0 1 ${x0 + (y1 - y0) / 2},${y1}
    Z
  `,
});

const buildWiggler: ShapeBuilder = ({ x0, x1, y0, y1 }) => {
  const width = x1 - x0;
  const peaks = 6;

  const points = Array.from({ length: peaks * 2 + 1 }, (_, i) => {
    const x = x0 + (i / (peaks * 2)) * width;
    const y = i % 2 === 0 ? y0 : y1;
    return `${i === 0 ? "M" : "L"} ${x},${y}`;
  });

  return {
    type: "path",
    path: [...points, `L ${x1},${y0}`, `L ${x0},${y0}`, "Z"].join(" "),
  };
};

const buildPhotonMonitor: ShapeBuilder = ({ x0, x1, y0, y1 }) => {
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;

  return {
    type: "path",
    path: [
      // diamond
      `M ${cx},${y1}`,
      `L ${x1},${cy}`,
      `L ${cx},${y0}`,
      `L ${x0},${cy}`,
      "Z",
    ].join(" "),
  };
};

// Define the configuration for each supported element type
// Each entry specifies how to build the shape, the CSS variables
// for fill and line colors, and the height of the element in the plot.
// Available element types are those that are returned 
// by the backend and may not be supported for plotting.
// Supported element types are those that have a corresponding entry in ELEMENT_PLOT_CONFIG
export const ELEMENT_PLOT_CONFIG = {
  Aperture: {
    buildShape: buildCircle,
    fillColorVariable: "--aperture-fill",
    lineColorVariable: "--aperture-line",
    height: 0.24,
  },

  Beam_Arrival_Monitor: {
    buildShape: buildDiamond,
    fillColorVariable: "--bam-fill",
    lineColorVariable: "--bam-line",
    height: 0.32,
  },

  Beam_Position_Monitor: {
    buildShape: buildDiamond,
    fillColorVariable: "--bpm-fill",
    lineColorVariable: "--bpm-line",
    height: 0.32,
  },

  Bunch_Length_Monitor: {
    buildShape: buildHexagon,
    fillColorVariable: "--blm-fill",
    lineColorVariable: "--blm-line",
    height: 0.32,
  },

  Collimator: {
    buildShape: buildTrapezoid,
    fillColorVariable: "--collimator-fill",
    lineColorVariable: "--collimator-line",
    height: 0.28,
  },

  Combined_Corrector: {
    buildShape: buildDoubleTriangle,
    fillColorVariable: "--corrector-fill",
    lineColorVariable: "--corrector-line",
    height: 0.28,
  },

  Dipole: {
    buildShape: buildTriangle,
    fillColorVariable: "--dipole-fill",
    lineColorVariable: "--dipole-line",
    height: 0.32,
  },

  Integrated_Current_Transformer: {
    buildShape: buildHexagon,
    fillColorVariable: "--ict-fill",
    lineColorVariable: "--ict-line",
    height: 0.32,
  },

  Marker: {
    buildShape: buildCross,
    fillColorVariable: "--marker-fill",
    lineColorVariable: "--marker-line",
    height: 0.25,
  },

  Plasma: {
    buildShape: buildRectangle,
    fillColorVariable: "--plasma-fill",
    lineColorVariable: "--plasma-line",
    height: 0.4,
  },

  Quadrupole: {
    buildShape: buildRectangle,
    fillColorVariable: "--quadrupole-fill",
    lineColorVariable: "--quadrupole-line",
    height: 0.32,
  },

  RFCavity: {
    buildShape: buildRectangle,
    fillColorVariable: "--rfcavity-fill",
    lineColorVariable: "--rfcavity-line",
    height: 0.24,
  },

  RFDeflectingCavity: {
    buildShape: buildHexagon,
    fillColorVariable: "--rfdeflector-fill",
    lineColorVariable: "--rfdeflector-line",
    height: 0.28,
  },

  Screen: {
    buildShape: buildCircle,
    fillColorVariable: "--screen-fill",
    lineColorVariable: "--screen-line",
    height: 0.4,
  },

  Sextupole: {
    buildShape: buildHourglass,
    fillColorVariable: "--sextupole-fill",
    lineColorVariable: "--sextupole-line",
    height: 0.32,
  },

  Shutter: {
    buildShape: buildHourglass,
    fillColorVariable: "--shutter-fill",
    lineColorVariable: "--shutter-line",
    height: 0.24,
  },

  Solenoid: {
    buildShape: buildCapsule,
    fillColorVariable: "--solenoid-fill",
    lineColorVariable: "--solenoid-line",
    height: 0.32,
  },

  Wall_Current_Monitor: {
    buildShape: buildHexagon,
    fillColorVariable: "--wcm-fill",
    lineColorVariable: "--wcm-line",
    height: 0.32,
  },
  Wiggler: {
    buildShape: buildWiggler,
    fillColorVariable: "--wiggler-fill",
    lineColorVariable: "--wiggler-line",
    height: 0.36,
  },
  Photon_Monitor: {
    buildShape: buildPhotonMonitor,
    fillColorVariable: "--photon-monitor-fill",
    lineColorVariable: "--photon-monitor-line",
    height: 0.32,
  },
} satisfies Record<string, ElementPlotConfig>;



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
  elements
    .filter((element) => isSupportedElementType(element.type))
    .map((element) => {
      // access directly since we know the type is valid after filtering
      const elementConfig = ELEMENT_PLOT_CONFIG[element.type];
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
  elements
    .filter((element) => isSupportedElementType(element.type))
    .map((element) => {
      // access directly since we know the type is valid after filtering
      const elementConfig = ELEMENT_PLOT_CONFIG[element.type];
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
