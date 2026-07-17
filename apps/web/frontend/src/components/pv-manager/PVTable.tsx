import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { memo, useMemo } from "react";

import { Table, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

import { PVTableBody } from "./PVTableBody";
import type { PVEntry, PVMode } from "@/types";

const COLUMNS: readonly {
  key: string;
  label: string;
  width: string;
  className?: string;
}[] = [
  { key: "status", label: "Status", width: "w-[140px]" },
  { key: "pvName", label: "PV Name", width: "" },
  { key: "mode", label: "Mode", width: "w-[120px]" },
  { key: "value", label: "Value", width: "w-[240px]" },
  { key: "label", label: "Label", width: "w-[160px]" },
  { key: "actions", label: "Actions", width: "w-[200px]" },
  { key: "remove", label: "Remove", width: "w-[72px]" },
];

const PVTable = memo(function PVTable({
  entries,
  filterText,
  filterModes,
  onRemove,
  onReorder,
}: {
  entries: PVEntry[];
  filterText: string;
  filterModes: readonly PVMode[];
  onRemove: (id: number) => void;
  onReorder: (activeId: PVEntry["id"], overId: PVEntry["id"]) => void;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    onReorder(active.id as PVEntry["id"], over.id as PVEntry["id"]);
  };

  const visibleEntries = useMemo(() => {
    const normalised = filterText.trim().toLowerCase();
    return entries.filter((entry) => {
      if (normalised && !entry.pvName.toLowerCase().includes(normalised)) {
        return false;
      }
      return filterModes.includes(entry.mode);
    });
  }, [entries, filterText, filterModes]);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[restrictToVerticalAxis]}
      onDragEnd={handleDragEnd}
    >
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            {COLUMNS.map((col) => (
              <TableHead key={col.key} className={cn(col.width, col.className)}>
                {col.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <SortableContext
          items={visibleEntries.map((entry) => entry.id)}
          strategy={verticalListSortingStrategy}
        >
          <PVTableBody
            entries={visibleEntries}
            onRemove={onRemove}
            columnCount={COLUMNS.length}
          />
        </SortableContext>
      </Table>
    </DndContext>
  );
});

PVTable.displayName = "PVTable";

export { PVTable };
