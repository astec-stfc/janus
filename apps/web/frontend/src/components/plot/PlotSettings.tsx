import { BinSizeSlider } from "@/components/plot/BinSizeSlider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import {
    GRID_SIZE_MAX,
    GRID_SIZE_MIN,
    type PlotSettingsState,
} from "@/hooks/usePlotSettings";

export function PlotSettings({ settings }: { settings: PlotSettingsState }) {
  const {
    plotType,
    handlePlotTypeChange,
    binSize,
    setBinSize,
    gridColumns,
    handleGridColumnsChange,
    gridRows,
    handleGridRowsChange,
    removeZOffset,
    setRemoveZOffset,
  } = settings;

  return (
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
                Algorithm decides optimal bin size up to max to best visualise distribution
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
                onChange={(event) => handleGridColumnsChange(event.target.value)}
              />
              <span className="text-sm">x</span>
              <Input
                id="grid-rows"
                type="number"
                min={GRID_SIZE_MIN}
                max={GRID_SIZE_MAX}
                value={gridRows}
                className="h-7 text-sm"
                onChange={(event) => handleGridRowsChange(event.target.value)}
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
  );
}
