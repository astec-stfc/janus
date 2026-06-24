import {
  buildPlotData,
  buildPlotLayout,
  getPlotRange,
  PLOT_CONFIG,
} from "@/components/plot/TwissPlotModel";
import { TwissElementTooltip } from "@/components/plot/TwissPlotTooltip";
import { useTwissElementTooltip } from "@/components/plot/useTwissElementTooltip";
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
  const { containerRef, tooltip, handleHover, handleUnhover } =
    useTwissElementTooltip();

  const range = useMemo(() => getPlotRange(beamSummaryData), [beamSummaryData]);
  const data = useMemo(
    () => buildPlotData(beamSummaryData, elements, range),
    [beamSummaryData, elements, range],
  );
  const layout = useMemo(
    () => buildPlotLayout(beamSummaryData.xParameter, elements, range),
    [beamSummaryData.xParameter, elements, range, theme],
  );

  return (
    <div ref={containerRef} className="relative h-full w-full">
      <Plot
        data={data}
        layout={layout}
        config={PLOT_CONFIG}
        onHover={handleHover}
        onUnhover={handleUnhover}
        useResizeHandler
        className="h-full w-full"
        style={{ width: "100%", height: "100%" }}
      />
      {tooltip && <TwissElementTooltip {...tooltip} />}
    </div>
  );
};

export default TwissPlot;
