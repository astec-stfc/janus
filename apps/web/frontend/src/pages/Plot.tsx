import PhaseSpaceSelector from "@/components/plot/PhaseSpaceSelector";
import PlotAreaContent from "@/components/plot/PlotAreaContent";
import { PlotSettings } from "@/components/plot/PlotSettings";
import SelectionList from "@/components/plot/SelectionList";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useBeamSelection } from "@/hooks/useBeamSelection";
import { usePhasePairs } from "@/hooks/usePhasePairs";
import { usePlotData } from "@/hooks/usePlotData";
import { usePlotSettings } from "@/hooks/usePlotSettings";

const Plot = () => {
  const settings = usePlotSettings();
  const selection = useBeamSelection();
  const data = usePlotData(
    selection.selectedUuid,
    selection.selectedBeam,
    settings.removeZOffset,
  );
  const { pairs, handleAddPair, handleRemovePair } = usePhasePairs();

  return (
    <div className="flex h-full">
      {/* Left panel */}
      <div className="flex w-72 shrink-0 flex-col gap-4 border-r p-4">
        <div className="min-h-0 flex-1 rounded-lg border">
          {/* UUID selector */}
          <SelectionList
            items={data.uuids.map((uuid) => ({ label: uuid, value: uuid }))}
            selectedItem={selection.selectedUuid}
            onSelect={selection.handleUuidSelect}
            placeholder="Search lattice runs..."
            emptyText={data.uuidEmptyText}
          />
        </div>
        <div className="min-h-0 flex-1 rounded-lg border">
          {/* Screen selector */}
          <SelectionList
            items={selection.beamOptions}
            selectedItem={selection.selectedBeam?.name ?? null}
            onSelect={selection.handleBeamSelection}
            placeholder="Search screens and markers..."
            emptyText={selection.beamEmptyText}
          />
        </div>
        <div className="rounded-lg border">
          <PhaseSpaceSelector
            pairs={pairs}
            onAddPair={handleAddPair}
            onRemovePair={handleRemovePair}
          />
        </div>
        <PlotSettings settings={settings} />
      </div>

      {/* Right panel */}
      <ScrollArea className="im-scrollbar flex-1 [container-type:size]">
        <PlotAreaContent
          beam={data.displayBeam}
          pairs={pairs}
          selectedUuid={selection.selectedUuid}
          selectedBeamName={selection.selectedBeam?.name ?? null}
          namesLoading={selection.namesLoading}
          beamLoading={data.beamLoading}
          beamLoadError={data.beamLoadError}
          gridColumns={settings.gridColumns}
          gridRows={settings.gridRows}
          plotType={settings.plotType}
          binSize={settings.binSize}
        />
      </ScrollArea>
    </div>
  );
};

export default Plot;
