import {
  buildPlotData,
  buildPlotLayout,
  getPlotRange,
  PLOT_CONFIG,
} from "@/components/plot/TwissPlotModel";
import { useTheme } from "@/hooks/useTheme";
import type { BeamSummaryData, PhysicalElement } from "@/types";
import { useMemo } from "react";
import Plot from "react-plotly.js";

interface TwissPlotProps {
  beamSummaryData: BeamSummaryData;
  elements: PhysicalElement[];
}

const TwissPlot = ({ beamSummaryData, elements }: TwissPlotProps) => {
  const { theme } = useTheme();
  const range = useMemo(() => getPlotRange(beamSummaryData), [beamSummaryData]);
  const data = useMemo(
    () => buildPlotData(beamSummaryData, range),
    [beamSummaryData, range],
  );
  const layout = useMemo(
    () => buildPlotLayout(beamSummaryData.xParameter, elements, range),
    [beamSummaryData.xParameter, elements, range, theme],
  );

  return (
    <Plot
      data={data}
      layout={layout}
      config={PLOT_CONFIG}
      useResizeHandler
      className="h-full w-full"
      style={{ width: "100%", height: "100%" }}
    />
  );
};

export default TwissPlot;
