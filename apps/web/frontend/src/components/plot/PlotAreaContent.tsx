import PhaseSpacePlot from "@/components/plot/PhaseSpacePlot";
import type { PlotType } from "@/components/plot/PhaseSpacePlot";
import type { Beam } from "@/types";

const CenteredMessage = ({ text }: { text: string }) => (
  <div className="flex h-[100cqh] items-center justify-center p-4 pr-5">
    <p className="text-sm text-muted-foreground">{text}</p>
  </div>
);

const clampGridSize = (value: number) => Math.max(1, Math.min(4, value));

const getGridAutoRows = (rows: number) => {
  const clampedRows = clampGridSize(rows);
  const rowHeight = 100 / clampedRows;

  // Accounts for p-4 on top+bottom (32px total) and row gaps (16px each).
  const pixelOffset = 16 + 16 / clampedRows;
  return `calc(${rowHeight}cqh - ${pixelOffset}px)`;
};

const PlotGrid = ({
  beam,
  pairs,
  gridColumns,
  gridRows,
  plotType,
  binSize,
}: {
  beam: Beam;
  pairs: [keyof Beam, keyof Beam][];
  gridColumns: number;
  gridRows: number;
  plotType: PlotType;
  binSize: number;
}) => {
  const clampedColumns = clampGridSize(gridColumns);

  return (
    <div
      className="grid gap-4 p-4"
      style={{
        gridTemplateColumns: `repeat(${clampedColumns}, minmax(0, 1fr))`,
        gridAutoRows: getGridAutoRows(gridRows),
      }}
    >
      {pairs.map(([xAxis, yAxis]) => (
        <div
          key={`${xAxis}-${yAxis}`}
          className="overflow-hidden rounded-lg border bg-muted/30"
        >
          <PhaseSpacePlot
            beam={beam}
            xAxis={xAxis}
            yAxis={yAxis}
            plotType={plotType}
            binSize={binSize}
          />
        </div>
      ))}
    </div>
  );
};

const PlotAreaContent = ({
  beam,
  pairs,
  selectedUuid,
  selectedBeamName,
  namesLoading,
  beamLoading,
  beamLoadError,
  gridColumns,
  gridRows,
  plotType,
  binSize,
}: {
  beam: Beam | null;
  pairs: [keyof Beam, keyof Beam][];
  selectedUuid: string | null;
  selectedBeamName: string | null;
  namesLoading: boolean;
  beamLoading: boolean;
  beamLoadError: string | null;
  gridColumns: number;
  gridRows: number;
  plotType: PlotType;
  binSize: number;
}) => {
  if (beam) {
    if (pairs.length === 0)
      return <CenteredMessage text="Add phase-space pairs to plot." />;
    return (
      <PlotGrid
        beam={beam}
        pairs={pairs}
        gridColumns={gridColumns}
        gridRows={gridRows}
        plotType={plotType}
        binSize={binSize}
      />
    );
  }
  if (selectedUuid && namesLoading) {
    return <CenteredMessage text="Loading screens and markers..." />;
  }
  if (selectedBeamName && beamLoading) {
    return <CenteredMessage text="Loading beam data..." />;
  }
  if (beamLoadError) return <CenteredMessage text={beamLoadError} />;
  if (selectedBeamName)
    return <CenteredMessage text="No beam data available for the selected item." />;
  if (selectedUuid) return <CenteredMessage text="Select a screen or marker." />;
  return (
    <CenteredMessage text="Select a run from the left to view phase space plots." />
  );
};

export default PlotAreaContent;
