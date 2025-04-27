import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';
import { chartColors, chartDefaults } from './config';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

interface PriceData {
  timestamp: number;
  price: number;
}

interface PriceChartProps {
  data: PriceData[];
  title?: string;
  height?: number;
  width?: number;
}

export function PriceChart({ data, title = 'Price Chart', height = 400, width = 800 }: PriceChartProps) {
  const chartData = {
    labels: data.map(item => new Date(item.timestamp)),
    datasets: [
      {
        label: 'Price',
        data: data.map(item => item.price),
        borderColor: chartColors.blue,
        backgroundColor: chartColors.lightBlue,
        tension: 0.1,
        fill: true,
        pointRadius: 0,
        pointHitRadius: 10,
      },
    ],
  };

  const options = {
    ...chartDefaults,
    plugins: {
      ...chartDefaults.plugins,
      title: {
        display: true,
        text: title,
      },
    },
    scales: {
      ...chartDefaults.scales,
      x: {
        ...chartDefaults.scales.x,
        type: 'time' as const,
        time: {
          unit: 'hour' as const,
          displayFormats: {
            hour: 'HH:mm',
          },
        },
        title: {
          display: true,
          text: 'Time',
        },
      },
      y: {
        ...chartDefaults.scales.y,
        title: {
          display: true,
          text: 'Price (USD)',
        },
      },
    },
  };

  return (
    <div style={{ height, width }}>
      <Line data={chartData} options={options} />
    </div>
  );
} 