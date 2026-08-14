import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ChevronDown, Columns3, Search } from "lucide-react";
import { useState } from "react";

import {
  RUN_COLUMN_GROUPS,
  RUN_COLUMNS,
  type RunColumnField,
} from "../runColumns";
import { CollapsibleGroup } from "./CollapsibleGroup";

interface ColumnSelectorProps {
  visibleFields: ReadonlySet<RunColumnField>;
  onVisibilityChange: (
    fields: readonly RunColumnField[],
    visible: boolean,
  ) => void;
}

export function ColumnSelector({
  visibleFields,
  onVisibilityChange,
}: ColumnSelectorProps) {
  const [searchInput, setSearchInput] = useState("");
  // Remember which groups the user has opened or closed.
  const [expandedGroupIds, setExpandedGroupIds] = useState<ReadonlySet<string>>(
    () => new Set(RUN_COLUMN_GROUPS.map(({ id }) => id)),
  );

  const searchQuery = searchInput.trim().toLowerCase();
  const isSearching = searchQuery.length > 0;

  const filteredGroups = RUN_COLUMN_GROUPS.map((group) => {
    const groupMatchesSearch = group.headerName
      .toLowerCase()
      .includes(searchQuery);
    // A matching group shows all its columns; otherwise show matching columns only.
    const matchingColumns = groupMatchesSearch
      ? group.columns
      : group.columns.filter(({ headerName }) =>
          headerName.toLowerCase().includes(searchQuery),
        );

    return { group, matchingColumns };
  }).filter(({ matchingColumns }) => matchingColumns.length > 0);

  const setGroupExpanded = (groupId: string, expanded: boolean) => {
    setExpandedGroupIds((currentGroupIds) => {
      const nextGroupIds = new Set(currentGroupIds);

      if (expanded) {
        nextGroupIds.add(groupId);
      } else {
        nextGroupIds.delete(groupId);
      }

      return nextGroupIds;
    });
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <Columns3 />
          Columns
          <span className="text-muted-foreground">
            {visibleFields.size}/{RUN_COLUMNS.length}
          </span>
          <ChevronDown />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" sideOffset={8} className="w-80 p-0">
        <div className="border-b p-3">
          <div className="relative">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
            <Input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search columns"
              className="pl-8"
            />
          </div>
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {filteredGroups.length === 0 && (
            <p className="text-muted-foreground px-2 py-6 text-center text-sm">
              No columns found.
            </p>
          )}
          {filteredGroups.map(({ group, matchingColumns }) => (
            <CollapsibleGroup
              key={group.id}
              group={group}
              matchingColumns={matchingColumns} // columns that match the search query
              visibleFields={visibleFields}
              // Expand while searching so matches are visible; clearing the
              // search restores the user's previous open/closed choice.
              isExpanded={isSearching || expandedGroupIds.has(group.id)}
              onExpandedChange={(expanded) =>
                setGroupExpanded(group.id, expanded)
              }
              onVisibilityChange={onVisibilityChange}
            />
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
