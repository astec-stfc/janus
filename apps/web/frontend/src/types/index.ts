// API Response Types
export interface HelloResponse {
  message: string;
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

export interface BeamSummary {
  position: number[];
  alpha_x: number[];
  beta_x: number[];
  alpha_y: number[];
  beta_y: number[];
  energy: number[];
  charge: number | null;
  n_particles: number | null;
  momentum: number[];
  emittance_x: number[];
  emittance_y: number[];
  normalised_emittance_x: number[];
  normalised_emittance_y: number[];
  sigma_x: number[];
  sigma_y: number[];
  sigma_t: number | null;
  centroids_x: number[];
  centroids_y: number[];
  centroids_t: number | null;
  cov_xx: number | null;
  cov_xxp: number | null;
  cov_yy: number | null;
  cov_yyp: number | null;
  cov_xy: number | null;
  cov_xyp: number | null;
}

export interface LatticeResponse {
  uuid: string;
  facility: string;
  beam_summary: BeamSummary | null;
}

export interface BeamSummaryParameter {
  name: keyof BeamSummary;
  label: string;
  unit?: string;
  values: number[];
}

export interface BeamSummaryData {
  xParameter: BeamSummaryParameter; // position along beamline
  yParameters: BeamSummaryParameter[]; // array of twiss parameters
}

export interface BeamSummaryPlotResponse {
  uuid: string;
  facility: string;
  beamSummaryData: BeamSummaryData | null;
}

export interface PhysicalElement {
  name: string;
  type: string;
  start: number;
  end: number;
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
