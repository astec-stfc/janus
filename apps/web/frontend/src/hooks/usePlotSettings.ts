import { DEFAULT_PLOT_TYPE, type PlotType } from "@/components/plot/PhaseSpacePlot";
import { useState } from "react";

export const GRID_SIZE_MIN = 1;
export const GRID_SIZE_MAX = 4;
const DEFAULT_BIN_SIZE = 128;

const clampGridSize = (value: number) =>
  Math.max(GRID_SIZE_MIN, Math.min(GRID_SIZE_MAX, value));

const isPlotType = (value: string): value is PlotType =>
  value === "density" || value === "scatter";

export function usePlotSettings() {
  const [gridColumns, setGridColumns] = useState(2);
  const [gridRows, setGridRows] = useState(2);
  const [plotType, setPlotType] = useState<PlotType>(DEFAULT_PLOT_TYPE);
  const [removeZOffset, setRemoveZOffset] = useState(true);
  const [binSize, setBinSize] = useState(DEFAULT_BIN_SIZE);

  const handleGridColumnsChange = (value: string) => {
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) return;
    setGridColumns(clampGridSize(parsed));
  };

  const handleGridRowsChange = (value: string) => {
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) return;
    setGridRows(clampGridSize(parsed));
  };

  const handlePlotTypeChange = (value: string) => {
    if (!isPlotType(value)) return;
    setPlotType(value);
  };

  return {
    gridColumns,
    gridRows,
    plotType,
    removeZOffset,
    binSize,
    setBinSize,
    setRemoveZOffset,
    handleGridColumnsChange,
    handleGridRowsChange,
    handlePlotTypeChange,
  };
}

export type PlotSettingsState = ReturnType<typeof usePlotSettings>;
