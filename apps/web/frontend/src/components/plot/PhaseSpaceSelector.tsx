import { useState } from "react";

import AxisInput from "@/components/plot/AxisInput";
import { badgeVariants } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ClosableBadge } from "@/components/ui/closable-badge";
import { cn } from "@/lib/utils";
import { BEAM_AXES } from "@/types";
import type { Beam } from "@/types";

interface PhaseSpaceSelectorProps {
  pairs: [keyof Beam, keyof Beam][];
  onAddPair: (pair: [keyof Beam, keyof Beam]) => void;
  onRemovePair: (pair: [keyof Beam, keyof Beam]) => void;
}

const PhaseSpaceSelector = ({
  pairs,
  onAddPair,
  onRemovePair,
}: PhaseSpaceSelectorProps) => {
  const [selectedAxes, setSelectedAxes] = useState<(keyof Beam)[]>([]);

  const handleAxisClick = (axis: keyof Beam) => {
    setSelectedAxes((prev) => {
      if (prev.includes(axis)) return prev.filter((a) => a !== axis);
      if (prev.length >= 2) return prev;
      return [...prev, axis];
    });
  };

  const handlePlot = () => {
    if (selectedAxes.length !== 2) return;
    onAddPair([selectedAxes[0], selectedAxes[1]]);
    setSelectedAxes([]);
  };

  return (
    <div className="grid gap-3 p-3">
      {/* Section 1: Axis buttons (x, y, z etc.)*/}
      <div className="grid grid-cols-3 gap-2">
        {BEAM_AXES.map(({ axis }) => {
          const isSelected = selectedAxes.includes(axis);
          return (
            <Button
              key={axis}
              size="sm"
              variant="outline"
              className={cn(
                "font-mono text-sm",
                isSelected && badgeVariants({ variant: "connected" }),
              )}
              onClick={() => handleAxisClick(axis)}
            >
              {axis}
            </Button>
          );
        })}
      </div>

      {/* Section 2: Placeholder inputs + Plot button */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <AxisInput
            label="X"
            value={selectedAxes[0] ?? ""}
            isNext={selectedAxes.length === 0}
          />
          <AxisInput
            label="Y"
            value={selectedAxes[1] ?? ""}
            isNext={selectedAxes.length === 1}
          />
        </div>
        <Button
          size="sm"
          disabled={!(selectedAxes.length === 2)}
          onClick={handlePlot}
        >
          Plot
        </Button>
      </div>

      {/* Section 3: Badge container*/}
      <div className="im-scrollbar flex h-12 flex-wrap content-start gap-1 overflow-y-auto rounded-md border">
        {pairs.map(([xAxis, yAxis]) => (
          <ClosableBadge
            key={`${xAxis}-${yAxis}`}
            variant="default"
            className="shrink-0"
            onClose={() => onRemovePair([xAxis, yAxis])}
          >
            {xAxis}-{yAxis}
          </ClosableBadge>
        ))}
      </div>
    </div>
  );
};

export default PhaseSpaceSelector;
