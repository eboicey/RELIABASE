import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Title,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Title);

export type ReliabilityCurvesProps = {
  times: number[];
  reliability: number[];
  hazard: number[];
};

export function ReliabilityCurves({ times, reliability, hazard }: ReliabilityCurvesProps) {
  // Format time labels (show every 10th or rounded subset)
  const step = Math.max(1, Math.floor(times.length / 10));
  const labels = times.map((t, i) => (i % step === 0 ? t.toFixed(0) : ""));

  const reliabilityData = {
    labels,
    datasets: [
      {
        label: "Reliability R(t)",
        data: reliability,
        borderColor: "rgba(94, 234, 212, 1)",
        backgroundColor: "rgba(94, 234, 212, 0.1)",
        fill: true,
        tension: 0.3,
        pointRadius: 0,
      },
    ],
  };

  const hazardData = {
    labels,
    datasets: [
      {
        label: "Hazard Rate h(t)",
        data: hazard,
        borderColor: "rgba(251, 146, 60, 1)",
        backgroundColor: "rgba(251, 146, 60, 0.1)",
        fill: true,
        tension: 0.3,
        pointRadius: 0,
      },
    ],
  };

  const reliabilityOptions = {
    responsive: true,
    plugins: {
      legend: { display: true, position: "top" as const },
      title: { display: true, text: "Reliability Function R(t)" },
    },
    scales: {
      x: {
        title: { display: true, text: "Time (hours)" },
        ticks: { maxTicksLimit: 10 },
      },
      y: {
        title: { display: true, text: "Reliability" },
        min: 0,
        max: 1,
      },
    },
  } as const;

  const hazardOptions = {
    responsive: true,
    plugins: {
      legend: { display: true, position: "top" as const },
      title: { display: true, text: "Hazard Function h(t)" },
    },
    scales: {
      x: {
        title: { display: true, text: "Time (hours)" },
        ticks: { maxTicksLimit: 10 },
      },
      y: {
        title: { display: true, text: "Hazard Rate" },
        min: 0,
      },
    },
  } as const;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="bg-ink-900/50 rounded-md p-4">
        <Line data={reliabilityData} options={reliabilityOptions} />
      </div>
      <div className="bg-ink-900/50 rounded-md p-4">
        <Line data={hazardData} options={hazardOptions} />
      </div>
    </div>
  );
}

export default ReliabilityCurves;
