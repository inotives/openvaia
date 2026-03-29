"use client";

import React, { useMemo } from "react";
import * as d3 from "d3";
import { STATUS_COLORS, STATUS_LABELS } from "@/lib/constants";

interface Props {
  data: Record<string, number>; // status -> count
  size?: number;
}

export default function TaskDonut({ data, size = 260 }: Props) {
  const chart = useMemo(() => {
    const entries = Object.entries(data).filter(([, v]) => v > 0);
    if (!entries.length) return null;

    const total = entries.reduce((a, [, v]) => a + v, 0);
    const pieGen = d3.pie<[string, number]>().value(([, v]) => v).sort(null);
    const arcs = pieGen(entries);

    const outerRadius = size / 2 - 30;
    const innerRadius = outerRadius * 0.6;
    const arcGen = d3.arc().innerRadius(innerRadius).outerRadius(outerRadius);

    const slices = arcs.map((a) => {
      const [status, count] = a.data;
      const color = antdToHex(STATUS_COLORS[status] || "default");
      return {
        status,
        count,
        path: arcGen(a as any) || "",
        color,
        label: STATUS_LABELS[status] || status,
      };
    });

    return { slices, total, innerRadius };
  }, [data, size]);

  if (!chart) {
    return (
      <div style={{ width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>
        No tasks
      </div>
    );
  }

  const cx = size / 2;
  const cy = size / 2;

  return (
    <svg width={size} height={size}>
      <g transform={`translate(${cx},${cy})`}>
        {chart.slices.map((s) => (
          <path key={s.status} d={s.path} fill={s.color} opacity={0.85} stroke="#fff" strokeWidth={2}>
            <title>{`${s.label}: ${s.count}`}</title>
          </path>
        ))}
        <text textAnchor="middle" dominantBaseline="middle" fontSize={22} fontWeight={700} fill="#262626">
          {chart.total}
        </text>
        <text textAnchor="middle" dominantBaseline="middle" y={20} fontSize={11} fill="#8c8c8c">
          tasks
        </text>
      </g>

      {/* Legend */}
      <g transform={`translate(${size + 8}, ${cy - chart.slices.length * 10})`}>
        {chart.slices.map((s, i) => (
          <g key={s.status} transform={`translate(0,${i * 22})`}>
            <rect width={12} height={12} rx={2} fill={s.color} />
            <text x={18} y={10} fontSize={11} fill="#595959">
              {s.label} ({s.count})
            </text>
          </g>
        ))}
      </g>
    </svg>
  );
}

/** Map Ant Design tag color names to hex. */
function antdToHex(color: string): string {
  const map: Record<string, string> = {
    default: "#d9d9d9",
    blue: "#1677ff",
    orange: "#fa8c16",
    green: "#52c41a",
    cyan: "#13c2c2",
    red: "#f5222d",
    purple: "#722ed1",
    geekblue: "#2f54eb",
    gold: "#faad14",
    volcano: "#fa541c",
    magenta: "#eb2f96",
    lime: "#a0d911",
  };
  return map[color] || color;
}
