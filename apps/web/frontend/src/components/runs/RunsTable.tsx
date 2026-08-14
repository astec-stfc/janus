import { useRunsQuery } from "@/queries/lattice.queries";
import type { RunSummary } from "@/types";
import { AgGridProvider, AgGridReact } from "ag-grid-react";
import { useMemo } from "react";

import { ColumnSelector } from "./column-selector/ColumnSelector";
import { createColumnDefs } from "./runColumns";
import {
  DEFAULT_COLUMN_SETTINGS,
  getRunRowId,
  RUNS_GRID_MODULES,
  RUNS_GRID_THEME,
} from "./runsGridConfig";
import { useRunColumnVisibility } from "./useRunColumnVisibility";

function NoColumnsOverlay() {
  return <span>Select one or more columns to display runs.</span>;
}

export function RunsTable() {
  const { data, isError, isLoading } = useRunsQuery();
  const { visibleFields, setColumnsVisible } = useRunColumnVisibility();
  const columnDefs = useMemo(
    () => createColumnDefs(visibleFields),
    [visibleFields],
  );

  const overlayComponentParams = {
    loading: { overlayText: "Loading runs…" },
    noRows: {
      overlayText: isError ? "Unable to load runs." : "No runs found.",
    },
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="flex justify-end">
        <ColumnSelector
          visibleFields={visibleFields}
          onVisibilityChange={setColumnsVisible}
        />
      </div>
      <div className="min-h-0 flex-1">
        <AgGridProvider modules={RUNS_GRID_MODULES}>
          <AgGridReact<RunSummary>
            activeOverlay={
              visibleFields.size === 0 ? NoColumnsOverlay : undefined
            }
            columnDefs={columnDefs}
            defaultColDef={DEFAULT_COLUMN_SETTINGS}
            enableCellTextSelection
            ensureDomOrder
            getRowId={getRunRowId}
            loading={isLoading}
            overlayComponentParams={overlayComponentParams}
            rowData={data ?? []}
            theme={RUNS_GRID_THEME}
          />
        </AgGridProvider>
      </div>
    </div>
  );
}
