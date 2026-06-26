import { TWISS_ELEMENT_HOVER_GROUP } from "@/components/plot/TwissPlotElements";
import type { PlotHoverEvent } from "plotly.js";
import { useRef, useState } from "react";

export interface TwissElementTooltipData {
  x: number;
  y: number;
  name: string;
  elementType: string;
}

const getTraceText = (text: string | string[] | undefined) =>
  Array.isArray(text) ? text[0] : text;

export const useTwissElementTooltip = () => {
  // lets the tooltip stay local to this plot (that `containerRef` is applied to),
  // avoiding page-level positioning
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<TwissElementTooltipData | null>(null);

  const handleHover = (plotlyHoverEvent: Readonly<PlotHoverEvent>) => {
    const point = plotlyHoverEvent.points[0];
    if (!point) {
      setTooltip(null);
      return;
    }

    // point.data is entire trace object (see return of `buildElementHoverTraces`)
    // Check if hover is over the invisible trace that represents our elements 
    if (point.data.legendgroup !== TWISS_ELEMENT_HOVER_GROUP) {
      setTooltip(null);
      return;
    }

    const traceText = getTraceText(point.data.text);
    if (!traceText) return;
    const [name, elementType] = traceText.split("\n");

    // get plot component container bounds in viewport coordinates
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseEvent = plotlyHoverEvent.event;
    // Store tooltip position relative to the plot container.
    setTooltip({
      x: mouseEvent.clientX - rect.left,
      y: mouseEvent.clientY - rect.top,
      name,
      elementType,
    });
  };

  const handleUnhover = () => setTooltip(null);

  return {
    containerRef,
    tooltip,
    handleHover,
    handleUnhover,
  };
};
