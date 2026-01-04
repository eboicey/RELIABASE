import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

export type ParetoChartProps = {
  labels: string[];
  values: number[];
};

export function ParetoChart({ labels, values }: ParetoChartProps) {
  const data = {
    labels,
    datasets: [
      {
        label: "Count",
        data: values,
        backgroundColor: "rgba(94, 234, 212, 0.7)",
        borderColor: "rgba(94, 234, 212, 1)",
        borderWidth: 1,
      },
    ],
  };

  const options = {
    plugins: { legend: { display: false } },
    scales: {
      y: {
        ticks: { precision: 0 },
        beginAtZero: true,
      },
    },
  } as const;

  return (
    <div className="bg-ink-900/50 rounded-md p-2">
      <Bar data={data} options={options} />
    </div>
  );
}

export default ParetoChart;
