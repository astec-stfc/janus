import * as echarts from "echarts";
import { useEffect, useRef } from "react";
import { useTheme } from "@/hooks/useTheme";
import { getCssVariable } from "@/lib/utils";
import type { ChartProps } from "@/types";
import type { CallbackDataParams } from "echarts/types/dist/shared";

import { format } from "d3-format";

const fmt = format(".3~g");

const ScatterChart = ({ xData, yData, xLabel, yLabel }: ChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const { theme } = useTheme();

  useEffect(() => {
    if (!containerRef.current) return;
    chartRef.current = echarts.init(containerRef.current);

    const observer = new ResizeObserver(() => chartRef.current?.resize());
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chartRef.current?.dispose();
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;

    const axis = getCssVariable("--chart-axis");
    const gridMajor = getCssVariable("--chart-grid-major");
    const gridMinor = getCssVariable("--chart-grid-minor");
    const data: [number, number][] = xData.map((x, i) => [x, yData[i]]);

    const axisStyle = {
      axisLine: { lineStyle: { color: axis } },
      axisTick: { lineStyle: { color: axis } },
      axisLabel: {
        color: axis,
        fontSize: 14,
        formatter: (value: number) => fmt(value),
      },
      nameTextStyle: { color: axis, fontSize: 16 },
      splitLine: { show: true, lineStyle: { color: gridMajor } },
      minorTick: { show: true },
      minorSplitLine: { show: true, lineStyle: { color: gridMinor } },
    };

    chartRef.current.setOption({
      grid: { top: 36, left: 8, right: 8, bottom: 8 },
      xAxis: {
        type: "value",
        scale: true,
        name: xLabel,
        nameLocation: "middle",
        nameGap: 28,
        ...axisStyle,
      },
      yAxis: {
        type: "value",
        scale: true,
        name: yLabel,
        nameLocation: "middle",
        nameGap: 48,
        ...axisStyle,
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0, filterMode: "empty" },
        { type: "inside", yAxisIndex: 0, filterMode: "empty" },
      ],
      toolbox: {
        show: true,
        right: 8,

        feature: {
          dataZoom: {
            xAxisIndex: 0,
            yAxisIndex: 0,
            title: { zoom: "Box zoom", back: "Reset zoom" },
          },
          restore: { title: "Reset" },
        },
        iconStyle: { borderColor: axis },
        emphasis: { iconStyle: { borderColor: gridMajor } },
      },
      series: [{ type: "scatter", symbolSize: 2, data }],
      tooltip: {
        trigger: "item",
        formatter: (p: CallbackDataParams) => {
          const [x, y] = p.value as [number, number];
          return `${xLabel}: ${fmt(x)}<br/>${yLabel}: ${fmt(y)}`;
        },
      },
    });
  }, [xData, yData, xLabel, yLabel, theme]);

  return <div ref={containerRef} className="h-full w-full" />;
};

export default ScatterChart;
