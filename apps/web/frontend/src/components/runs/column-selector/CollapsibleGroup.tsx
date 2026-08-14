import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { Check, ChevronRight, Minus } from "lucide-react";

import type {
  RunColumnConfig,
  RunColumnField,
  RunColumnGroup,
} from "../runColumns";

type SelectionState = "checked" | "unchecked" | "indeterminate";

function getGroupSelectionState(
  group: RunColumnGroup,
  visibleFields: ReadonlySet<RunColumnField>, // Fields currently shown in the table.
): SelectionState {
  const visibleCount = group.columns.filter(({ field }) =>
    visibleFields.has(field),
  ).length;

  if (visibleCount === 0) return "unchecked";
  if (visibleCount === group.columns.length) return "checked";
  return "indeterminate";
}

function SelectionIndicator({ state }: { state: SelectionState }) {
  return (
    <span
      className={cn(
        "flex size-4 shrink-0 items-center justify-center rounded-[4px] border",
        state === "unchecked"
          ? "border-input bg-background"
          : "border-primary bg-primary text-primary-foreground",
      )}
    >
      {state === "checked" && <Check className="size-3" strokeWidth={3} />}
      {state === "indeterminate" && (
        <Minus className="size-3" strokeWidth={3} />
      )}
    </span>
  );
}

function ColumnOption({
  column,
  isVisible,
  onToggle,
}: {
  column: RunColumnConfig;
  isVisible: boolean;
  onToggle: () => void;
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={onToggle}
      className="w-full justify-start px-2 font-normal"
    >
      <SelectionIndicator state={isVisible ? "checked" : "unchecked"} />
      <span className="truncate">{column.headerName}</span>
    </Button>
  );
}

interface CollapsibleGroupProps {
  group: RunColumnGroup;
  matchingColumns: readonly RunColumnConfig[];
  visibleFields: ReadonlySet<RunColumnField>;
  isExpanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
  onVisibilityChange: (
    fields: readonly RunColumnField[],
    visible: boolean,
  ) => void;
}

export function CollapsibleGroup({
  group,
  matchingColumns,
  visibleFields,
  isExpanded,
  onExpandedChange,
  onVisibilityChange,
}: CollapsibleGroupProps) {
  // The group toggle always controls the complete group, even during a search.
  const groupFields = group.columns.map(({ field }) => field);
  const groupSelectionState = getGroupSelectionState(group, visibleFields);

  return (
    <Collapsible open={isExpanded} onOpenChange={onExpandedChange}>
      <div className="flex h-8 items-center">
        <CollapsibleTrigger asChild>
          <Button type="button" variant="ghost" size="icon-sm">
            <ChevronRight className={cn("size-4", isExpanded && "rotate-90")} />
          </Button>
        </CollapsibleTrigger>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() =>
            onVisibilityChange(groupFields, groupSelectionState !== "checked")
          }
          className="min-w-0 flex-1 justify-start px-1"
        >
          <SelectionIndicator state={groupSelectionState} />
          <span className="truncate">{group.headerName}</span>
        </Button>
      </div>
      <CollapsibleContent>
        <div className="border-border ml-4 border-l py-1 pl-7">
          {matchingColumns.map((column) => {
            const isVisible = visibleFields.has(column.field);

            return (
              <ColumnOption
                key={column.field}
                column={column}
                isVisible={isVisible}
                onToggle={() => onVisibilityChange([column.field], !isVisible)}
              />
            );
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
