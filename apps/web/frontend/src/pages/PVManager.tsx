import {
  FilterModeButtonGroup,
  ModeButtonGroup,
} from "@/components/pv-manager/ModeButtonGroup";
import { PVTable } from "@/components/pv-manager/PVTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MODE_OPTIONS, type PVEntry, type PVMode } from "@/types";
import { arrayMove } from "@dnd-kit/sortable";
import { useCallback, useRef, useState } from "react";

export default function PVManager() {
  const nextId = useRef(1);

  const [pvName, setPvName] = useState("");
  const [mode, setMode] = useState<PVMode>("MONITOR");
  const [entries, setEntries] = useState<PVEntry[]>([]);
  const [filterText, setFilterText] = useState("");
  const [isAllMode, setIsAllMode] = useState(true);
  const [activeModes, setActiveModes] = useState<PVMode[]>([...MODE_OPTIONS]);

  const addEntry = () => {
    const name = pvName.trim();
    if (name === "") return;

    const entry: PVEntry = {
      id: nextId.current++,
      pvName: name,
      mode,
    };

    setEntries((prev) => [...prev, entry]);
    setPvName("");
  };

  const removeEntry = useCallback((id: number) => {
    setEntries((prev) => prev.filter((entry) => entry.id !== id));
  }, []);

  const reorderEntries = useCallback(
    (activeId: PVEntry["id"], overId: PVEntry["id"]) => {
      setEntries((prev) => {
        // find index of PVEntry in PVEntry list before dragging occurred
        const oldIndex = prev.findIndex((entry) => entry.id === activeId);
        // find index position that we want to move it to
        const newIndex = prev.findIndex((entry) => entry.id === overId);
        return arrayMove(prev, oldIndex, newIndex);
      });
    },
    [],
  );

  const toggleAll = useCallback(() => {
    if (isAllMode) {
      // ALL is active -> clicking it again deselects everything
      setIsAllMode(false);
      setActiveModes([]);
    } else {
      setIsAllMode(true);
      setActiveModes([...MODE_OPTIONS]);
    }
  }, [isAllMode]);

  const toggleFilterMode = useCallback(
    (modeToToggle: PVMode) => {
      // clicking an individual mode always exits ALL mode first
      setIsAllMode(false);
      setActiveModes((prev) => {
        // if `ALL` was active *before* toggle, then prev = [...MODE_OPTIONS]
        // and `isAllMode` is still True, so we need to reset it to [] first.
        const current = isAllMode ? [] : prev;
        const isSelected = current.includes(modeToToggle);
        return isSelected
          ? current.filter((m) => m !== modeToToggle)
          : [...current, modeToToggle];
      });
    },
    [isAllMode],
  );

  const resetFilters = useCallback(() => {
    setFilterText("");
    setIsAllMode(true);
    setActiveModes([...MODE_OPTIONS]);
  }, []);

  return (
    <ScrollArea className="h-full min-h-0">
      <div className="flex w-full flex-col gap-6 p-6 pr-7">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            addEntry();
          }}
          className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-end gap-6"
        >
          <label className="flex flex-col gap-2">
            <span className="text-sm font-medium">PV Name</span>
            <Input
              value={pvName}
              onChange={(event) => setPvName(event.target.value)}
              placeholder="PV name (e.g. ca://... or pva://...)"
            />
          </label>
          <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
            <legend className="p-0 text-sm font-medium">Mode</legend>
            <ModeButtonGroup value={mode} onChange={setMode} />
          </fieldset>
          <div className="flex flex-col gap-2">
            <span
              className="text-sm font-medium text-transparent"
              aria-hidden="true"
            >
              Action
            </span>
            <Button type="submit" className="h-9 min-w-[88px]">
              Add PV
            </Button>
          </div>
        </form>

        <div className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-end gap-6">
          <label className="flex flex-col gap-2">
            <span className="text-sm font-medium">Filter PVs</span>
            <Input
              value={filterText}
              onChange={(event) => setFilterText(event.target.value)}
              placeholder="Type to filter"
            />
          </label>
          <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
            <legend className="p-0 text-sm font-medium">Filter Mode</legend>
            <FilterModeButtonGroup
              isAllMode={isAllMode}
              activeModes={activeModes}
              onToggleAll={toggleAll}
              onToggleMode={toggleFilterMode}
            />
          </fieldset>
          <div className="flex flex-col gap-2">
            <span
              className="text-sm font-medium text-transparent"
              aria-hidden="true"
            >
              Action
            </span>
            <Button
              type="button"
              variant="secondary"
              className="h-9 min-w-[88px]"
              onClick={resetFilters}
            >
              RESET
            </Button>
          </div>
        </div>

        <div className="w-full">
          <PVTable
            entries={entries}
            filterText={filterText}
            filterModes={activeModes}
            onRemove={removeEntry}
            onReorder={reorderEntries}
          />
        </div>
      </div>
    </ScrollArea>
  );
}
