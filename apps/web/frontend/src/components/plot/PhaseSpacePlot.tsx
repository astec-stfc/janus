import type { Beam, ChartProps } from "@/types";
import { BEAM_AXES } from "@/types";
import type { ComponentType } from "react";
import DensityChart from "./DensityChart";
import ScatterChart from "./ScatterChart";

export type PlotType = "density" | "scatter";
export const DEFAULT_PLOT_TYPE: PlotType = "density";

interface PhaseSpacePlotProps {
  beam: Beam;
  xAxis: keyof Beam;
  yAxis: keyof Beam;
  plotType: PlotType;
  binSize: number;
}

const chartComponents: Record<PlotType, ComponentType<ChartProps>> = {
  density: DensityChart,
  scatter: ScatterChart,
};

const getAxisLabel = (key: keyof Beam): string => {
  const def = BEAM_AXES.find((a) => a.axis === key);
  return def ? `${key} (${def.unit})` : key;
};

const PhaseSpacePlot = ({
  beam,
  xAxis,
  yAxis,
  plotType,
  binSize,
}: PhaseSpacePlotProps) => {
  const xData = beam[xAxis];
  const yData = beam[yAxis];

  if (!xData || !yData) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground font-mono">
        No data for {xAxis} vs {yAxis}
      </div>
    );
  }

  const Chart = chartComponents[plotType];
  const xLabel = getAxisLabel(xAxis);
  const yLabel = getAxisLabel(yAxis);

  return (
    <Chart
      xData={xData}
      yData={yData}
      xLabel={xLabel}
      yLabel={yLabel}
      binSize={binSize}
    />
  );
};

export default PhaseSpacePlot;
