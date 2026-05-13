import {
  DEFAULT_PLOT_TYPE,
  type PlotType,
} from "@/components/plot/PhaseSpacePlot";
import PhaseSpaceSelector from "@/components/plot/PhaseSpaceSelector";
import PlotAreaContent from "@/components/plot/PlotAreaContent";
import SelectionList from "@/components/plot/SelectionList";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Slider } from "@/components/ui/slider";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import latticeService from "@/services/lattice";
import type { Beam } from "@/types";
import { subtractMean } from "@/lib/utils";
import { useCallback, useEffect, useMemo, useState } from "react";

const GRID_SIZE_MIN = 1;
const GRID_SIZE_MAX = 4;
const DEFAULT_BIN_SIZE = 16;
const BIN_SIZE_MIN = 8;
const BIN_SIZE_MAX = 128;
const DEFAULT_PAIRS: [keyof Beam, keyof Beam][] = [
  ["x", "cpx"],
  ["y", "cpy"],
  ["z", "cpz"],
  ["x", "y"],
];

interface BinSizeSliderProps {
  value: number;
  onCommit: (value: number) => void;
  disabled: boolean;
}

const BinSizeSlider = ({
  value,
  onCommit,
  disabled = false,
}: BinSizeSliderProps) => {
  const [localValue, setLocalValue] = useState(value);
  return (
    <div className="flex w-full items-center gap-3">
      <Slider
        min={BIN_SIZE_MIN}
        max={BIN_SIZE_MAX}
        value={[localValue]}
        disabled={disabled}
        onValueChange={(v) => setLocalValue(v[0])}
        onValueCommit={(v) => {
          setLocalValue(v[0]);
          onCommit(v[0]);
        }}
      />
      <span className={disabled ? "text-muted-foreground" : undefined}>
        {localValue}
      </span>
    </div>
  );
};

const clampGridSize = (value: number) =>
  Math.max(GRID_SIZE_MIN, Math.min(GRID_SIZE_MAX, value));

const isPlotType = (value: string): value is PlotType =>
  value === "density" || value === "scatter";

const Plot = () => {
  const [uuids, setUuids] = useState<string[]>([]);
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null);
  const [screenNames, setScreenNames] = useState<string[]>([]);
  const [selectedScreenName, setSelectedScreenName] = useState<string | null>(
    null,
  );
  const [beam, setBeam] = useState<Beam | null>(null);
  const [pairs, setPairs] = useState<[keyof Beam, keyof Beam][]>(() => [
    ...DEFAULT_PAIRS,
  ]);
  const [gridColumns, setGridColumns] = useState(2);
  const [gridRows, setGridRows] = useState(2);
  const [plotType, setPlotType] = useState<PlotType>(DEFAULT_PLOT_TYPE);
  const [removeZOffset, setRemoveZOffset] = useState(true);
  const [binSize, setBinSize] = useState(DEFAULT_BIN_SIZE);

  const displayBeam = useMemo<Beam | null>(() => {
    if (!beam) return null;
    if (!removeZOffset || !beam.z) return beam;
    return { ...beam, z: subtractMean(beam.z) };
  }, [beam, removeZOffset]);

  useEffect(() => {
    latticeService.getRunUuids().then(setUuids);
  }, []);

  useEffect(() => {
    if (!selectedUuid) return;
    setSelectedScreenName(null);
    setScreenNames([]);
    setBeam(null);
    latticeService.getScreenNames(selectedUuid).then(setScreenNames);
  }, [selectedUuid]);

  useEffect(() => {
    if (!selectedUuid || !selectedScreenName) return;
    setBeam(null);
    latticeService
      .getScreenBeam(selectedUuid, selectedScreenName)
      .then(setBeam);
  }, [selectedUuid, selectedScreenName]);

  const handleAddPair = useCallback(
    (pair: [keyof Beam, keyof Beam]) => {
      const isDuplicate = pairs.some(
        ([a, b]) => a === pair[0] && b === pair[1],
      );
      if (!isDuplicate) setPairs((prev) => [...prev, pair]);
    },
    [pairs],
  );

  const handleRemovePair = useCallback((pair: [keyof Beam, keyof Beam]) => {
    setPairs((prev) => prev.filter(([a, b]) => a !== pair[0] || b !== pair[1]));
  }, []);

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

  return (
    /* Page root: [left panel] [right panel] */
    <div className="flex h-full">
      {/* Left panel */}
      <div className="flex w-72 shrink-0 flex-col gap-4 border-r p-4">
        {/* UUID list box */}
        <div className="min-h-0 flex-1 rounded-lg border">
          <SelectionList
            items={uuids}
            selectedItem={selectedUuid}
            onSelect={setSelectedUuid}
            placeholder="Search lattice runs..."
            emptyText="No runs found"
          />
        </div>

        {/* Screen list box */}
        <div className="min-h-0 flex-1 rounded-lg border">
          <SelectionList
            items={screenNames}
            selectedItem={selectedScreenName}
            onSelect={setSelectedScreenName}
            placeholder="Search screens..."
            emptyText={selectedUuid ? "No screens found." : "Select a run"}
          />
        </div>

        {/* Phase-space pair selector */}
        <div className="rounded-lg border">
          <PhaseSpaceSelector
            pairs={pairs}
            onAddPair={handleAddPair}
            onRemovePair={handleRemovePair}
          />
        </div>

        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" className="w-full">
              Settings
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-96" align="start">
            <div className="grid gap-2">
              <div className="grid grid-cols-2 items-center gap-4">
                <Label htmlFor="plot-type">Plot Type</Label>
                <ToggleGroup
                  id="plot-type"
                  type="single"
                  value={plotType}
                  onValueChange={handlePlotTypeChange}
                  className="grid h-9 grid-cols-2"
                >
                  <ToggleGroupItem value="density" className="h-full">
                    Density
                  </ToggleGroupItem>
                  <ToggleGroupItem value="scatter" className="h-full">
                    Scatter
                  </ToggleGroupItem>
                </ToggleGroup>
              </div>
              <div className="grid grid-cols-2 items-center gap-4">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Label htmlFor="bin-size">(Maximum) Bin Size</Label>
                  </TooltipTrigger>
                  <TooltipContent side="top">
                    Algorithm decides optimal bin size up to max to best
                    visualise distribution
                  </TooltipContent>
                </Tooltip>
                <div className="flex h-9 items-center">
                  <BinSizeSlider
                    value={binSize}
                    onCommit={setBinSize}
                    disabled={plotType !== "density"}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 items-center gap-4">
                <Label htmlFor="grid-columns">Grid Size</Label>
                <div className="flex h-9 items-center gap-2">
                  <Input
                    id="grid-columns"
                    type="number"
                    min={GRID_SIZE_MIN}
                    max={GRID_SIZE_MAX}
                    value={gridColumns}
                    className="h-7 text-sm"
                    onChange={(event) =>
                      handleGridColumnsChange(event.target.value)
                    }
                  />
                  <span className="text-sm">x</span>
                  <Input
                    id="grid-rows"
                    type="number"
                    min={GRID_SIZE_MIN}
                    max={GRID_SIZE_MAX}
                    value={gridRows}
                    className="h-7 text-sm"
                    onChange={(event) =>
                      handleGridRowsChange(event.target.value)
                    }
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 items-center gap-4">
                <Label htmlFor="remove-z-offset">Remove Z Offset</Label>
                <div className="flex h-9 items-center">
                  <Switch
                    id="remove-z-offset"
                    checked={removeZOffset}
                    onCheckedChange={setRemoveZOffset}
                  />
                </div>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Right panel window Frame: fixed size with scrollbar for inner content */}
      <ScrollArea className="im-scrollbar flex-1 [container-type:size]">
        <PlotAreaContent
          beam={displayBeam}
          pairs={pairs}
          selectedUuid={selectedUuid}
          selectedScreenName={selectedScreenName}
          gridColumns={gridColumns}
          gridRows={gridRows}
          plotType={plotType}
          binSize={binSize}
        />
      </ScrollArea>
    </div>
  );
};

export default Plot;
