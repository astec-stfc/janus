import type { TwissElementTooltipData } from "@/components/plot/useTwissElementTooltip";

export const TwissElementTooltip = ({
  x,
  y,
  name,
  elementType,
}: TwissElementTooltipData) => (
  <div
    className="pointer-events-none absolute z-10 rounded border bg-popover px-2 py-1 text-xs text-popover-foreground"
    style={{
      left: x,
      top: y,
      transform: "translate(-50%, calc(-100% - 32px))",
    }}
  >
    <p className="font-semibold">{name}</p>
    <p className="text-muted-foreground">{elementType}</p>
  </div>
);
