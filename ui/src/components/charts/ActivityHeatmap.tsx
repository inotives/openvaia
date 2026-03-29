"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";

interface DayData {
  date: string;
  count: number;
}

interface Props {
  data: DayData[];
  width?: number;
  height?: number;
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function ActivityHeatmap({ data, width: propWidth, height = 160 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [measuredWidth, setMeasuredWidth] = useState(propWidth || 700);

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
    const marginLeft = 36;
    const marginTop = 20;

    // Build lookup — normalize date keys to YYYY-MM-DD
    const lookup: Record<string, number> = {};
    for (const d of data) lookup[d.date.slice(0, 10)] = d.count;

    // Generate last ~6 months of dates
    const today = new Date();
    const start = new Date(today);
    start.setMonth(start.getMonth() - 6);
    // Align to Monday
    const dayOfWeek = start.getDay();
    const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    start.setDate(start.getDate() + mondayOffset);

    const days: { date: Date; dateStr: string; count: number; col: number; row: number }[] = [];
    const monthLabels: { label: string; col: number }[] = [];
    let lastMonth = -1;
    let col = 0;

    const cursor = new Date(start);
    while (cursor <= today) {
      const row = (cursor.getDay() + 6) % 7; // Mon=0, Sun=6
      if (row === 0 && days.length > 0) col++;

      const dateStr = cursor.toISOString().slice(0, 10);
      const count = lookup[dateStr] || 0;

      // Month label on first Monday of a new month
      if (cursor.getMonth() !== lastMonth && row === 0) {
        monthLabels.push({ label: MONTH_NAMES[cursor.getMonth()], col });
        lastMonth = cursor.getMonth();
      }

      days.push({ date: new Date(cursor), dateStr, count, col, row });
      cursor.setDate(cursor.getDate() + 1);
    }

    const maxCount = Math.max(...days.map((d) => d.count), 1);
    const totalCols = col + 1;

    // Dynamic cell size to fill available width
    const availableW = width - marginLeft - 10;
    const cellGap = 3;
    const cellSize = Math.max(8, Math.floor((availableW - (totalCols - 1) * cellGap) / totalCols));
    const step = cellSize + cellGap;

    const colorScale = d3
      .scaleLinear<string>()
      .domain([0, 1, maxCount * 0.33, maxCount * 0.66, maxCount])
      .range(["#1a1a2e", "#0e4429", "#006d32", "#26a641", "#39d353"]);

    const computedWidth = marginLeft + totalCols * step + 10;

    return { days, monthLabels, colorScale, cellSize, step, marginLeft, marginTop, computedWidth, maxCount };
  }, [data, width]);

  return (
    <div ref={containerRef} style={{ width: "100%", overflowX: "auto" }}>
      <svg width={chart.computedWidth} height={height} style={{ overflow: "visible" }}>
        {/* Day labels */}
        {DAY_LABELS.map((label, i) => (
          <text
            key={label}
            x={chart.marginLeft - 8}
            y={chart.marginTop + i * chart.step + chart.cellSize / 2}
            fontSize={10}
            fill="rgba(255,255,255,0.4)"
            textAnchor="end"
            dominantBaseline="central"
          >
            {i % 2 === 0 ? label : ""}
          </text>
        ))}

        {/* Month labels */}
        {chart.monthLabels.map((m, i) => (
          <text
            key={`${m.label}-${i}`}
            x={chart.marginLeft + m.col * chart.step}
            y={chart.marginTop - 6}
            fontSize={10}
            fill="rgba(255,255,255,0.5)"
          >
            {m.label}
          </text>
        ))}

        {/* Cells */}
        {chart.days.map((d) => (
          <rect
            key={d.dateStr}
            x={chart.marginLeft + d.col * chart.step}
            y={chart.marginTop + d.row * chart.step}
            width={chart.cellSize}
            height={chart.cellSize}
            rx={2}
            fill={chart.colorScale(d.count)}
            stroke="rgba(255,255,255,0.03)"
            strokeWidth={0.5}
          >
            <title>{`${d.dateStr}: ${d.count} task${d.count !== 1 ? "s" : ""} completed`}</title>
          </rect>
        ))}

        {/* Legend */}
        <g transform={`translate(${chart.computedWidth - 140}, ${height - 16})`}>
          <text fontSize={10} fill="rgba(255,255,255,0.4)" y={10}>Less</text>
          {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
            <rect
              key={i}
              x={30 + i * 16}
              y={0}
              width={12}
              height={12}
              rx={2}
              fill={chart.colorScale(t * chart.maxCount)}
            />
          ))}
          <text fontSize={10} fill="rgba(255,255,255,0.4)" x={30 + 5 * 16} y={10}>More</text>
        </g>
      </svg>
    </div>
  );
}
