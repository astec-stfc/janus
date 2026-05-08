import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import type { Config, Data, Layout } from "plotly.js";

import { useTheme } from "@/providers/ThemeProvider";
import type { ChartProps } from "@/types";

const getCssVar = (name: string): string =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const PLOT_TICK_FORMAT = ".3~g";

const buildLayout = (xLabel: string, yLabel: string): Partial<Layout> => {
  const axis = getCssVar("--chart-axis");
  const gridMajor = getCssVar("--chart-grid-major");
  return {
    autosize: true,
    margin: { t: 36, l: 56, r: 24, b: 52 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: axis, size: 14 },
    xaxis: {
      color: axis,
      title: { text: xLabel, standoff: 10 },
      automargin: true,
      tickformat: PLOT_TICK_FORMAT,
      showgrid: true,
      gridcolor: gridMajor,
      zeroline: false,
      linecolor: axis,
    },
    yaxis: {
      color: axis,
      title: { text: yLabel, standoff: 10 },
      automargin: true,
      tickformat: PLOT_TICK_FORMAT,
      showgrid: true,
      gridcolor: gridMajor,
      zeroline: false,
      linecolor: axis,
    },
  };
};

const DensityChart = ({
  xData,
  yData,
  xLabel,
  yLabel,
  binSize = 16,
}: ChartProps) => {
  const { theme } = useTheme();

  const trace = useMemo<Data>(
    () => ({
      type: "histogram2d",
      x: xData,
      y: yData,
      nbinsx: binSize,
      nbinsy: binSize,
      colorscale: "Viridis",
      colorbar: { tickformat: PLOT_TICK_FORMAT },
    }),
    [xData, yData, binSize],
  );

  const [layout, setLayout] = useState<Partial<Layout>>(() =>
    buildLayout(xLabel, yLabel),
  );
  useEffect(() => {
    setLayout(buildLayout(xLabel, yLabel));
  }, [theme]);

  const config = useMemo<Partial<Config>>(
    () => ({
      responsive: true,
      displaylogo: false,
      scrollZoom: true,
    }),
    [],
  );

  return (
    <Plot
      data={[trace]}
      layout={layout}
      config={config}
      useResizeHandler
      style={{ width: "100%", height: "100%" }}
      className="h-full w-full"
    />
  );
};

export default DensityChart;
