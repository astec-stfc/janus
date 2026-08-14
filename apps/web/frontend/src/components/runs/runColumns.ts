import type { RunSummary } from "@/types";
import type { ColDef } from "ag-grid-community";

const EMPTY_VALUE = "—";

const timestampFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "medium",
});

export type RunColumnField = keyof RunSummary;

export interface RunColumnConfig extends ColDef<RunSummary> {
  field: RunColumnField;
  headerName: string;
  defaultVisible: boolean;
}

export interface RunColumnGroup {
  id: string;
  headerName: string;
  columns: readonly RunColumnConfig[];
}

const LATTICE_RUN_COLUMNS = [
  {
    field: "uuid",
    headerName: "UUID",
    defaultVisible: true,
    flex: 2,
    minWidth: 300,
  },
  {
    field: "facility",
    headerName: "Facility",
    defaultVisible: true,
    flex: 1,
    minWidth: 160,
  },
  {
    field: "timestamp",
    headerName: "Timestamp",
    defaultVisible: true,
    flex: 1.25,
    minWidth: 220,
    valueFormatter: ({ value }) =>
      value ? timestampFormatter.format(new Date(value)) : EMPTY_VALUE,
  },
  {
    field: "client_id",
    headerName: "Client ID",
    defaultVisible: true,
    flex: 1.25,
    minWidth: 180,
    valueFormatter: ({ value }) => value ?? EMPTY_VALUE,
  },
  {
    field: "success",
    headerName: "Success",
    defaultVisible: true,
    cellDataType: "boolean",
    cellRendererParams: { disabled: true },
    flex: 0.6,
    minWidth: 120,
  },
] as const satisfies readonly RunColumnConfig[];

// Grouped form used by the column selector.
export const RUN_COLUMN_GROUPS = [
  {
    id: "lattice",
    headerName: "Lattice",
    columns: LATTICE_RUN_COLUMNS,
  },
] as const satisfies readonly RunColumnGroup[];

// Extract columns from all groups (only lattice group so far).
export const RUN_COLUMNS: readonly RunColumnConfig[] =
  RUN_COLUMN_GROUPS.flatMap(({ columns }) => columns);

// Get default visible run column fields
export function getDefaultFields(): Set<RunColumnField> {
  return new Set(
    RUN_COLUMNS.filter(({ defaultVisible }) => defaultVisible).map(
      ({ field }) => field,
    ),
  );
}

export function createColumnDefs(
  visibleFields: ReadonlySet<RunColumnField>,
): ColDef<RunSummary>[] {
  return RUN_COLUMNS.filter(({ field }) => visibleFields.has(field)).map(
    ({ defaultVisible, ...colDef }) => colDef,
  );
}
