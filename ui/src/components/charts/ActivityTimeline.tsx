"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";

interface TimelinePoint {
  date: string;
  tasks_created: number;
  tasks_completed: number;
  messages_sent: number;
}

interface Props {
  data: TimelinePoint[];
  width?: number;
  height?: number;
}

const SERIES = [
  { key: "messages_sent", label: "Messages", color: "#722ed1" },
  { key: "tasks_created", label: "Created", color: "#1677ff" },
  { key: "tasks_completed", label: "Completed", color: "#52c41a" },
] as const;

export default function ActivityTimeline({ data, width: propWidth, height = 200 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [measuredWidth, setMeasuredWidth] = useState(propWidth || 500);

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 0) setMeasuredWidth(w);
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const width = propWidth || measuredWidth;

  const chart = useMemo(() => {
    if (!data.length) return null;

    const margin = { top: 16, right: 100, bottom: 30, left: 36 };
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    const dates = data.map((d) => new Date(d.date));
    const allVals = data.flatMap((d) => [d.tasks_created, d.tasks_completed, d.messages_sent]);
    const maxVal = Math.max(...allVals, 1);

    const x = d3.scaleTime().domain(d3.extent(dates) as [Date, Date]).range([0, w]);
    const y = d3.scaleLinear().domain([0, maxVal]).nice().range([h, 0]);

    const lineGen = (key: string) =>
      d3
        .line<TimelinePoint>()
        .x((_, i) => x(dates[i]))
        .y((d) => y((d as any)[key]))
        .curve(d3.curveMonotoneX);

    const lines = SERIES.map((s) => ({
      ...s,
      path: lineGen(s.key)(data) || "",
    }));

    const xTicks = x.ticks(6).map((t) => ({ val: t, x: x(t) }));
    const yTicks = y.ticks(4).map((t) => ({ val: t, y: y(t) }));

    return { lines, xTicks, yTicks, x, y, w, h, margin };
  }, [data, width, height]);

  if (!chart) {
    return (
      <div ref={containerRef} style={{ width: "100%", height, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>
        No activity data
      </div>
    );
  }

  const { margin } = chart;

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <svg width={width} height={height}>
        <g transform={`translate(${margin.left},${margin.top})`}>
          {/* Grid */}
          {chart.yTicks.map((t) => (
            <g key={t.val}>
              <line x1={0} x2={chart.w} y1={t.y} y2={t.y} stroke="rgba(255,255,255,0.06)" />
              <text x={-8} y={t.y} fontSize={10} fill="rgba(255,255,255,0.4)" textAnchor="end" dominantBaseline="middle">
                {t.val}
              </text>
            </g>
          ))}

          {/* X axis */}
          {chart.xTicks.map((t) => (
            <text key={t.val.toISOString()} x={t.x} y={chart.h + 18} fontSize={10} fill="rgba(255,255,255,0.4)" textAnchor="middle">
              {d3.timeFormat("%b %d")(t.val)}
            </text>
          ))}

          {/* Lines */}
          {chart.lines.map((l) => (
            <path key={l.key} d={l.path} fill="none" stroke={l.color} strokeWidth={2} opacity={0.85} />
          ))}

          {/* Legend */}
          <g transform={`translate(${chart.w + 12}, 0)`}>
            {chart.lines.map((l, i) => (
              <g key={l.key} transform={`translate(0,${i * 20})`}>
                <line x1={0} x2={16} y1={6} y2={6} stroke={l.color} strokeWidth={2} />
                <text x={22} y={10} fontSize={11} fill="rgba(255,255,255,0.6)">{l.label}</text>
              </g>
            ))}
          </g>
        </g>
      </svg>
    </div>
  );
}
