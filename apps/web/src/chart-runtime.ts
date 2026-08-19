import * as echarts from "echarts/core";
import type { EChartsOption } from "echarts";
import { BarChart, GraphChart, LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  GraphChart,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  CanvasRenderer,
]);

export function createChart(element: HTMLElement, option: EChartsOption) {
  const chart = echarts.init(element);
  chart.setOption(option);
  return chart;
}
