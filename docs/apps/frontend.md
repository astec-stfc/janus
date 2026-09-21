# Web Frontend

The JANUS web frontend is a React application for browsing simulation runs, inspecting beam data, plotting Twiss parameters, and interacting with EPICS process variables. It is built from the frontend in [`apps/web/frontend`](https://github.com/astec-stfc/janus/blob/develop/apps/web/frontend/).

The application uses the Lattice API and RESTFrame services for simulation data and connects to the PVWS service for live PV access.

## Navigation

The frontend provides the following routes:

| Route | Purpose |
|---|---|
| `/pv-manager` | Monitor and control EPICS PVs |
| `/runs` | Browse stored simulation runs |
| `/plot` | Explore beam phase-space data |
| `/plot-twiss` | Plot Twiss parameters for a selected run |

## Runs table

The Runs page presents stored lattice runs in an interactive AG Grid table. Run data is loaded from the Lattice API.

The table supports:

- Loading and empty states when runs are unavailable.
- Error feedback when the runs request fails.
- Selecting which columns are visible.
- Selecting text from cells.
- Stable row identity for efficient updates.
- Horizontal and vertical inspection of run metadata.

The table is intended as the starting point for identifying a lattice UUID to use with the plotting tools.

## Beam plots

The Plot page provides interactive phase-space plots for beam data associated with screens and markers.

The workflow is:

1. Select a lattice run by UUID.
2. Select a screen or marker from the available beam locations.
3. Select one or more phase-space coordinate pairs.
4. Inspect the resulting beam distribution plots.
5. Adjust plot settings such as the grid layout, bin size, plot type, and Z-offset handling.

Beam data is loaded through the lattice and HSDS services. The frontend requests the domain/path references for the selected beam location and uses those references to retrieve the underlying arrays.

The plot area supports responsive resizing and can display multiple coordinate-pair plots in a configurable grid.

## Twiss plots

The Plot Twiss page accepts a lattice UUID and renders the available Twiss data for that run.

The plot contains:

- Twiss traces for `alpha_x`, `alpha_y`, `beta_x`, and `beta_y`.
- A beamline schematic beneath the Twiss graph.
- Physical accelerator elements positioned along the beamline.
- Hover interaction for identifying plotted elements.
- Responsive Plotly rendering and scroll zoom.

Twiss data is obtained from the Lattice API's beam-summary data. Physical element information is obtained from RESTFrame so the plot can show the accelerator layout alongside the Twiss traces. A plot is shown only when the selected run contains compatible, non-empty data for the plotted parameters.

## PV Control

The PV Manager provides browser-based access to EPICS PVs through the PVWS service. PV entries can be added, removed, filtered, reordered, and assigned an operating mode.

The manager supports:

- **GET** - request the current value of a PV on demand.
- **Monitor** - subscribe to continuous updates from a PV.
- **PUT** - write a numeric value to a PV when write access is enabled.
- Connection and error status for each PV.
- Value and label display based on the incoming PV data.
- Filtering by PV name and operating mode.
- Drag-and-drop reordering of PV entries.
- Copying PV names to the clipboard.

The frontend maintains shared subscriptions and cached values through `PVWSProvider`. If the WebSocket connection is interrupted, active PV subscriptions are restored when the connection returns.

The PVWS URL can be configured with `VITE_PVWS_URL`. If it is not set, the frontend uses the current browser host and `VITE_PVWS_PORT`, which defaults to port `8080`.

## Data services

The frontend communicates with JANUS services through the configured development proxy or deployment URLs:

- **Lattice API** - run metadata, lattice UUIDs, beam references, and beam-summary/Twiss data.
- **RESTFrame** - physical accelerator element data used by the Twiss beamline schematic.
- **HSDS backend** - binary beam-array payloads referenced by lattice data.
- **PVWS** - WebSocket bridge for EPICS PV subscriptions and writes.

The frontend does not store simulation arrays locally. It requests metadata and references from the APIs and loads beam data when a user selects a run and beam location.

## Frontend source

- [Application routes](https://github.com/astec-stfc/janus/blob/develop/apps/web/frontend/src/routes.ts)
- [Runs page](https://github.com/astec-stfc/janus/blob/develop/apps/web/frontend/src/pages/Runs.tsx)
- [Beam plot page](https://github.com/astec-stfc/janus/blob/develop/apps/web/frontend/src/pages/Plot.tsx)
- [Twiss plot page](https://github.com/astec-stfc/janus/blob/develop/apps/web/frontend/src/pages/PlotTwiss.tsx)
- [PV Manager components](https://github.com/astec-stfc/janus/blob/develop/apps/web/frontend/src/components/pv-manager/)
- [PVWS provider](https://github.com/astec-stfc/janus/blob/develop/apps/web/frontend/src/providers/PVWSProvider.tsx)
