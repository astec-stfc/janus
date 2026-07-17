import { Slider } from "@/components/ui/slider";
import { useState } from "react";

const BIN_SIZE_MIN = 8;
const BIN_SIZE_MAX = 256;

interface BinSizeSliderProps {
  value: number;
  onCommit: (value: number) => void;
  disabled?: boolean;
}

export const BinSizeSlider = ({
  value,
  onCommit,
  disabled = false,
}: BinSizeSliderProps) => {
  const [localValue, setLocalValue] = useState(value);
  return (
    <div className="flex w-full items-center gap-3">
      <Slider
        min={BIN_SIZE_MIN}
        max={BIN_SIZE_MAX}
        value={[localValue]}
        disabled={disabled}
        onValueChange={(v) => setLocalValue(v[0])}
        onValueCommit={(v) => {
          setLocalValue(v[0]);
          onCommit(v[0]);
        }}
      />
      <span className={disabled ? "text-muted-foreground" : undefined}>
        {localValue}
      </span>
    </div>
  );
};
