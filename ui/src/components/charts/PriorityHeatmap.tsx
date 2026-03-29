"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";

interface PriorityRow {
  priority: string;
  status: string;
  count: number;
}

interface Props {
  data: PriorityRow[];
  width?: number;
  height?: number;
}

const PRIORITIES = ["critical", "high", "medium", "low"];
const STATUSES = ["backlog", "todo", "in_progress", "review", "done", "blocked"];
const STATUS_SHORT: Record<string, string> = {
  backlog: "Back",
  todo: "Todo",
  in_progress: "WIP",
  review: "Rev",
  done: "Done",
  blocked: "Block",
};

export default function PriorityHeatmap({ data, width: propWidth, height = 220 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [measuredWidth, setMeasuredWidth] = useState(propWidth || 360);

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

    const margin = { top: 30, right: 10, bottom: 10, left: 60 };
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    const cellW = w / STATUSES.length;
    const cellH = h / PRIORITIES.length;

    const lookup: Record<string, number> = {};
    for (const r of data) lookup[`${r.priority}-${r.status}`] = r.count;

    const maxVal = Math.max(...data.map((d) => d.count), 1);
    const colorScale = d3
      .scaleSequential(d3.interpolateBlues)
      .domain([0, maxVal]);

    const cells = PRIORITIES.flatMap((p, pi) =>
      STATUSES.map((s, si) => {
        const val = lookup[`${p}-${s}`] || 0;
        return {
          key: `${p}-${s}`,
          x: si * cellW,
          y: pi * cellH,
          w: cellW,
          h: cellH,
          val,
          fill: val > 0 ? colorScale(val) : "rgba(255,255,255,0.04)",
          textColor: val > maxVal * 0.6 ? "#fff" : "rgba(255,255,255,0.7)",
          priority: p,
          status: s,
        };
      }),
    );

    return { cells, cellW, cellH, margin };
  }, [data, width, height]);

  if (!chart) {
    return (
      <div ref={containerRef} style={{ width: "100%", height, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>
        No data
      </div>
    );
  }

  const { margin } = chart;

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <svg width={width} height={height}>
        <g transform={`translate(${margin.left},${margin.top})`}>
          {/* Column headers */}
          {STATUSES.map((s, i) => (
            <text
              key={s}
              x={i * chart.cellW + chart.cellW / 2}
              y={-10}
              fontSize={10}
              fill="rgba(255,255,255,0.4)"
              textAnchor="middle"
            >
              {STATUS_SHORT[s]}
            </text>
          ))}

          {/* Row headers */}
          {PRIORITIES.map((p, i) => (
            <text
              key={p}
              x={-8}
              y={i * chart.cellH + chart.cellH / 2}
              fontSize={11}
              fill="rgba(255,255,255,0.5)"
              textAnchor="end"
              dominantBaseline="middle"
              style={{ textTransform: "capitalize" }}
            >
              {p}
            </text>
          ))}

          {/* Cells */}
          {chart.cells.map((c) => (
            <g key={c.key}>
              <rect x={c.x} y={c.y} width={c.w - 2} height={c.h - 2} rx={3} fill={c.fill} stroke="rgba(255,255,255,0.08)" strokeWidth={0.5}>
                <title>{`${c.priority} / ${c.status}: ${c.val}`}</title>
              </rect>
              {c.val > 0 && (
                <text
                  x={c.x + c.w / 2 - 1}
                  y={c.y + c.h / 2 - 1}
                  fontSize={12}
                  fontWeight={600}
                  fill={c.textColor}
                  textAnchor="middle"
                  dominantBaseline="middle"
                >
                  {c.val}
                </text>
              )}
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
