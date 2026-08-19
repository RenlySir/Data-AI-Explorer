import * as echarts from "echarts/core";
import type { EChartsOption } from "echarts";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

export function createChart(element: HTMLElement, option: EChartsOption) {
  const chart = echarts.init(element);
  chart.setOption(option);
  return chart;
}
