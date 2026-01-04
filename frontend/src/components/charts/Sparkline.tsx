import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

export type SparklineProps = {
  labels: string[];
  values: number[];
};

export function Sparkline({ labels, values }: SparklineProps) {
  const data = {
    labels,
    datasets: [
      {
        label: "MTBF (hours)",
        data: values,
        borderColor: "rgba(94, 234, 212, 1)",
        backgroundColor: "rgba(94, 234, 212, 0.15)",
        fill: true,
        tension: 0.35,
        pointRadius: 2,
      },
    ],
  };

  const options = {
    plugins: { legend: { display: false } },
    scales: {
      x: { display: false },
      y: {
        display: true,
        ticks: { precision: 0 },
        beginAtZero: true,
      },
    },
  } as const;

  return (
    <div className="bg-ink-900/50 rounded-md p-2">
      <Line data={data} options={options} />
    </div>
  );
}

export default Sparkline;
