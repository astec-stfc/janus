import { Clipboard } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";

interface SelectionListProps {
  items: string[];
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
        {items.map((item) => (
          <CommandItem
            key={item}
            value={item}
            onSelect={() => {
              onSelect(item);
              navigator.clipboard.writeText(item);
            }}
            className={cn(
              "relative group",
              selectedItem === item && "bg-accent text-accent-foreground",
            )}
          >
            <span className="truncate font-mono text-s">{item}</span>
            <Clipboard className="absolute right-2 size-3 opacity-0 pointer-events-none transition-opacity group-hover:opacity-40" />
          </CommandItem>
        ))}
      </CommandList>
    </Command>
  );
};

export default SelectionList;
