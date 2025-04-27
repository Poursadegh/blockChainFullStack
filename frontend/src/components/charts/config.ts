export const chartColors = {
  green: 'rgb(75, 192, 75)',
  red: 'rgb(192, 75, 75)',
  blue: 'rgb(75, 75, 192)',
  lightGreen: 'rgba(75, 192, 75, 0.2)',
  lightRed: 'rgba(192, 75, 75, 0.2)',
  lightBlue: 'rgba(75, 75, 192, 0.2)',
};

export const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: 'index' as const,
  },
  plugins: {
    legend: {
      position: 'top' as const,
    },
    tooltip: {
      enabled: true,
      mode: 'index' as const,
      intersect: false,
    },
  },
  scales: {
    x: {
      grid: {
        display: false,
      },
    },
    y: {
      grid: {
        color: 'rgba(200, 200, 200, 0.1)',
      },
      ticks: {
        callback: (value: number) => `$${value.toLocaleString()}`,
      },
    },
  },
};

export const timeIntervals = {
  '1m': 60 * 1000,
  '5m': 5 * 60 * 1000,
  '15m': 15 * 60 * 1000,
  '30m': 30 * 60 * 1000,
  '1h': 60 * 60 * 1000,
  '4h': 4 * 60 * 60 * 1000,
  '1d': 24 * 60 * 60 * 1000,
  '1w': 7 * 24 * 60 * 60 * 1000,
};

export const d3ChartDefaults = {
  margin: { top: 20, right: 30, bottom: 30, left: 40 },
  colors: {
    bid: chartColors.green,
    ask: chartColors.red,
    buy: chartColors.green,
    sell: chartColors.red,
    default: chartColors.blue,
  },
  animation: {
    duration: 300,
  },
  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderColor: 'rgba(0, 0, 0, 0.1)',
    borderWidth: 1,
    borderRadius: 4,
    padding: 8,
    fontSize: 12,
  },
}; 