import type { LucideIcon } from "lucide-react";
import { Activity, ChartLine, Download, Home, Table2 } from "lucide-react";
import type { ComponentType } from "react";

import DownloadComponent from "@/pages/Download";
import HomeComponent from "@/pages/Home";
import PVManagerComponent from "@/pages/PVManager";
import PlotComponent from "@/pages/Plot";
import PlotTwissComponent from "@/pages/PlotTwiss";
import RunsComponent from "@/pages/Runs";

export interface AppRoute {
  path: string;
  label: string;
  icon: LucideIcon;
  component: ComponentType;
}

export const appRoutes: AppRoute[] = [
  { path: "/", label: "Home", icon: Home, component: HomeComponent },
  {
    path: "/download",
    label: "Download",
    icon: Download,
    component: DownloadComponent,
  },
  {
    path: "/pv-manager",
    label: "PV Manager",
    icon: Activity,
    component: PVManagerComponent,
  },
  { path: "/runs", label: "Runs", icon: Table2, component: RunsComponent },
  { path: "/plot", label: "Plot", icon: ChartLine, component: PlotComponent },
  {
    path: "/plot-twiss",
    label: "Plot Twiss",
    icon: ChartLine,
    component: PlotTwissComponent,
  },
];
