import { Input } from "@/components/ui/input";
import { connectedTextClasses } from "@/components/ui/variants";
import { cn } from "@/lib/utils";
import type { Beam } from "@/types";

interface AxisInputProps {
  label: "X" | "Y";
  value: keyof Beam | "";
  isNext: boolean;
}

const AxisInput = ({ label, value, isNext }: AxisInputProps) => (
  <div className="relative flex-1">
    <span
      className={cn(
        "pointer-events-none absolute top-1/2 left-2 -translate-y-1/2 text-xs text-muted-foreground transition-colors",
        isNext && connectedTextClasses,
      )}
    >
      {label}:
    </span>
    <Input
      readOnly
      value={value}
      variant={isNext ? "connected" : "default"}
      className="h-8 pl-6 font-mono text-xs transition-colors"
      tabIndex={-1}
    />
  </div>
);

export default AxisInput;
