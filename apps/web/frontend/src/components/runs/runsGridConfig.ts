import type { RunSummary } from "@/types";
import {
    AllCommunityModule,
    themeQuartz,
    type ColDef,
    type GetRowIdParams,
} from "ag-grid-community";

export const RUNS_GRID_MODULES = [AllCommunityModule];

export const DEFAULT_COLUMN_SETTINGS: ColDef<RunSummary> = {
  editable: false,
  filter: false,
  resizable: true,
  sortable: true,
  suppressHeaderMenuButton: true,
  suppressMovable: true,
};

export const RUNS_GRID_THEME = themeQuartz.withParams({
  accentColor: "var(--primary)",
  backgroundColor: "var(--background)",
  borderColor: "var(--border)",
  borderRadius: "var(--radius)",
  browserColorScheme: "inherit",
  fontFamily: "inherit",
  foregroundColor: "var(--foreground)",
  headerBackgroundColor: "var(--muted)",
  headerTextColor: "var(--muted-foreground)",
  rowHoverColor: "var(--accent)",
  subtleTextColor: "var(--muted-foreground)",
  wrapperBorderRadius: "var(--radius)",
});

export const getRunRowId = ({ data }: GetRowIdParams<RunSummary>) => data.uuid;
