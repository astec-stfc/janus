import { Clipboard } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";

interface SelectionItem {
  label: string;
  value: string;
}

type SelectionListItem = string | SelectionItem;

const normalizeSelectionItem = (item: SelectionListItem): SelectionItem =>
  typeof item === "string" ? { label: item, value: item } : item;

interface SelectionListProps {
  items: SelectionListItem[];
  selectedItem: string | null;
  onSelect: (value: string) => void;
  placeholder: string;
  emptyText: string;
}

const SelectionList = ({
  items,
  selectedItem,
  onSelect,
  placeholder,
  emptyText,
}: SelectionListProps) => {
  return (
    <Command>
      <CommandInput className="font-mono text-s" placeholder={placeholder} />
      <CommandList className="im-scrollbar flex-1 max-h-none overflow-y-auto">
        <CommandEmpty>{emptyText}</CommandEmpty>
        {items.map((item) => {
          const normalizedItem = normalizeSelectionItem(item);
          return (
          <CommandItem
            key={normalizedItem.value}
            value={normalizedItem.value}
            onSelect={() => {
              onSelect(normalizedItem.value);
              navigator.clipboard.writeText(normalizedItem.value);
            }}
            className={cn(
              "relative group",
              selectedItem === normalizedItem.value && "bg-accent text-accent-foreground",
            )}
          >
            <span className="truncate font-mono text-s">{normalizedItem.label}</span>
            <Clipboard className="absolute right-2 size-3 opacity-0 pointer-events-none transition-opacity group-hover:opacity-40" />
          </CommandItem>
          );
        })}
      </CommandList>
    </Command>
  );
};

export default SelectionList;
