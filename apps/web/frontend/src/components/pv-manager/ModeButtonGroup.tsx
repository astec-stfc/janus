import { Button } from "@/components/ui/button";

import type { PVMode } from "@/types";
import { MODE_OPTIONS } from "@/types";

const baseClass =
  "rounded-none first:rounded-l-md last:rounded-r-md -ml-px first:ml-0 transition-none";

export function ModeButtonGroup({
  value,
  onChange,
}: {
  value: PVMode;
  onChange: (mode: PVMode) => void;
}) {
  return (
    <div className="inline-flex">
      {MODE_OPTIONS.map((option) => {
        const isSelected = value === option;
        return (
          <Button
            key={option}
            type="button"
            variant={isSelected ? "secondary" : "outline"}
            className={baseClass}
            onClick={() => onChange(option)}
            aria-pressed={isSelected}
          >
            {option}
          </Button>
        );
      })}
    </div>
  );
}

export function FilterModeButtonGroup({
  isAllMode,
  activeModes,
  onToggleAll,
  onToggleMode,
}: {
  isAllMode: boolean;
  activeModes: readonly PVMode[];
  onToggleAll: () => void;
  onToggleMode: (mode: PVMode) => void;
}) {
  return (
    <div className="inline-flex">
      <Button
        type="button"
        variant={isAllMode ? "secondary" : "outline"}
        className={baseClass}
        onClick={onToggleAll}
        aria-pressed={isAllMode}
      >
        ALL
      </Button>
      {MODE_OPTIONS.map((option) => {
        const isSelected = !isAllMode && activeModes.includes(option);
        return (
          <Button
            key={option}
            type="button"
            variant={isSelected ? "secondary" : "outline"}
            className={baseClass}
            onClick={() => onToggleMode(option)}
            aria-pressed={isSelected}
          >
            {option}
          </Button>
        );
      })}
    </div>
  );
}
