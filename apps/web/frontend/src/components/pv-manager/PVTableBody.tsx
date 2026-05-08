import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { TableBody, TableCell, TableRow } from "@/components/ui/table";

import { PVRowCells } from "./PVRowCells";
import type { PVEntry } from "@/types";

function SortablePVRow({
  entry,
  onRemove,
}: {
  entry: PVEntry;
  onRemove: (id: number) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: entry.id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <TableRow
      ref={setNodeRef}
      style={style}
      className="hover:bg-muted/50"
      {...attributes}
      {...listeners}
    >
      <PVRowCells entry={entry} onRemove={onRemove} />
    </TableRow>
  );
}

export function PVTableBody({
  entries,
  onRemove,
  columnCount,
}: {
  entries: PVEntry[];
  onRemove: (id: number) => void;
  columnCount: number;
}) {
  if (entries.length === 0) {
    return (
      <TableBody>
        <TableRow>
          <TableCell colSpan={columnCount} className="text-muted-foreground">
            No PVs to display.
          </TableCell>
        </TableRow>
      </TableBody>
    );
  }

  return (
    <TableBody>
      {entries.map((entry) => (
        <SortablePVRow key={entry.id} entry={entry} onRemove={onRemove} />
      ))}
    </TableBody>
  );
}
