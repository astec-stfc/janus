// API Response Types
export interface HelloResponse {
  message: string;
}

// Blog Types
export interface Blog {
  id?: string;
  title: string;
  author: string;
  url?: string;
  likes?: number;
}

// Notification Types
export type NotificationType = "success" | "error" | "info" | null;

export interface NotificationProps {
  message: string | null;
  type: NotificationType;
}

export interface Beam {
  x: number[] | null;
  y: number[] | null;
  z: number[] | null;
  cpx: number[] | null;
  cpy: number[] | null;
  cpz: number[] | null;
}

export interface BeamAxisDef {
  axis: keyof Beam;
  unit: string;
}

export const BEAM_AXES: BeamAxisDef[] = [
  { axis: "x", unit: "m" },
  { axis: "y", unit: "m" },
  { axis: "z", unit: "m" },
  { axis: "cpx", unit: "eV/c" },
  { axis: "cpy", unit: "eV/c" },
  { axis: "cpz", unit: "eV/c" },
];

// PV Manager Types
export const MODE_OPTIONS = ["GET", "MONITOR", "PUT"] as const;
export type PVMode = (typeof MODE_OPTIONS)[number];

export type PVStatus = "connected" | "disconnected" | "invalid" | "awaiting";

export interface PVEntry {
  id: number;
  pvName: string;
  mode: PVMode;
}

export interface ChartProps {
  xData: number[];
  yData: number[];
  xLabel: string;
  yLabel: string;
  binSize: number;
}
