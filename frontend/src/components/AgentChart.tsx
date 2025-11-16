import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import styled from "styled-components";
import { useRef, useState } from "react";
// 👇 --- 1. IMPORT THE NEW LIBRARY ---
import { toPng, toBlob } from "html-to-image";

// The shape of the JSON we expect from the agent
interface AgentChartSpec {
  chartType: "bar" | "line" | "point" | string;
  xField: string;
  yField: string;
  data: Record<string, unknown>[];
}

interface AgentChartProps {
  spec: AgentChartSpec;
}

// --- 2. STYLED COMPONENTS (New & Updated) ---

const ChartContainer = styled.div`
  /* Set a specific height for the chart container */
  width: 100%;
  height: 300px;
  background: white;
  padding: 20px 10px 10px 0px;
  border-radius: 4px;
  margin-top: 5px;
  margin-bottom: 5px;

  /* Fix for text rendering in recharts tooltips */
  .recharts-tooltip-label,
  .recharts-tooltip-item {
    color: #333;
  }
`;

const ButtonContainer = styled.div`
  display: flex;
  gap: 10px;
  margin-top: 10px;
  padding-left: 50px; /* Aligns with chart padding */
`;

const ChartButton = styled.button`
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 4px;
  border: 1px solid #ccc;
  background-color: #f9f9f9;
  color: #333;
  cursor: pointer;

  &:hover:not(:disabled) {
    background-color: #f1f1f1;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

// --- 3. THE COMPONENT ---

export const AgentChart = ({ spec }: AgentChartProps) => {
  const { chartType, data, xField, yField } = spec;

  // 👇 --- 4. ADD REFS AND STATE ---
  const chartRef = useRef<HTMLDivElement>(null);
  const [copyButtonText, setCopyButtonText] = useState("Copy");

  // 👇 --- 5. ADD HANDLER FUNCTIONS ---
  const handleDownload = () => {
    if (chartRef.current === null) {
      return;
    }

    toPng(chartRef.current, { cacheBust: true })
      .then((dataUrl) => {
        const link = document.createElement("a");
        link.download = "chart.png";
        link.href = dataUrl;
        link.click();
      })
      .catch((err) => {
        console.error("Failed to download chart", err);
      });
  };

  const handleCopy = () => {
    if (chartRef.current === null) {
      return;
    }

    toBlob(chartRef.current, { cacheBust: true })
      .then((blob) => {
        if (!blob) {
          throw new Error("Failed to create blob");
        }

        // Use the modern clipboard API
        const item = new ClipboardItem({ "image/png": blob });
        navigator.clipboard.write([item]).then(
          () => {
            setCopyButtonText("Copied!");
            setTimeout(() => setCopyButtonText("Copy"), 2000);
          },
          (err) => {
            console.error("Failed to copy image", err);
          }
        );
      })
      .catch((err) => {
        console.error("Failed to copy chart", err);
      });
  };

  const renderChart = () => {
    switch (chartType) {
      case "bar":
        return (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xField} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey={yField} fill="#0d47a1" />
          </BarChart>
        );

      case "line":
        return (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xField} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey={yField} stroke="#0d4t7a1" activeDot={{ r: 8 }} />
          </LineChart>
        );

      case "point":
        return (
          <ScatterChart>
            <CartesianGrid />
            <XAxis type="category" dataKey={xField} name={xField} />
            <YAxis type="number" dataKey={yField} name={yField} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter name="Data" data={data} fill="#0d47a1" />
          </ScatterChart>
        );

      default:
        return <div>Unsupported chart type: {chartType}</div>;
    }
  };

  // 👇 --- 6. UPDATE THE RETURNED JSX ---
  return (
    <>
      {/* This div is now the target for our ref.
        We pass the ref to the *wrapper* of ResponsiveContainer.
      */}
      <ChartContainer ref={chartRef}>
        <ResponsiveContainer width="100%" height="100%">
          {renderChart()}
        </ResponsiveContainer>
      </ChartContainer>

      <ButtonContainer>
        <ChartButton onClick={handleDownload}>Download</ChartButton>
        <ChartButton onClick={handleCopy} disabled={copyButtonText === "Copied!"}>
          {copyButtonText}
        </ChartButton>
      </ButtonContainer>
    </>
  );
};
