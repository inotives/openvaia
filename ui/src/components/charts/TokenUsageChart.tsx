"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";

interface TokenDay {
  date: string;
  input_tokens: number;
  output_tokens: number;
}

interface Props {
  data: TokenDay[];
  width?: number;
  height?: number;
}

const SERIES = [
  { key: "input_tokens", label: "Input", color: "#1677ff" },
  { key: "output_tokens", label: "Output", color: "#fa541c" },
] as const;

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

export default function TokenUsageChart({ data, width: propWidth, height = 200 }: Props) {
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

    const margin = { top: 16, right: 100, bottom: 30, left: 44 };
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    const dates = data.map((d) => new Date(d.date));
    const maxVal = Math.max(...data.map((d) => d.input_tokens + d.output_tokens), 1);

    const x = d3.scaleBand<Date>()
      .domain(dates)
      .range([0, w])
      .padding(0.3);

    const y = d3.scaleLinear().domain([0, maxVal]).nice().range([h, 0]);

    const bars = data.map((d, i) => {
      const inputH = h - y(d.input_tokens);
      const outputH = h - y(d.output_tokens);
      return {
        date: dates[i],
        dateStr: d.date,
        x: x(dates[i]) || 0,
        barWidth: x.bandwidth(),
        input: { y: h - inputH - outputH, height: inputH, value: d.input_tokens },
        output: { y: h - outputH, height: outputH, value: d.output_tokens },
        total: d.input_tokens + d.output_tokens,
      };
    });

    const xTicks = dates.filter((_, i) => {
      const step = Math.max(1, Math.floor(dates.length / 8));
      return i % step === 0;
    });
    const yTicks = y.ticks(4).map((t) => ({ val: t, y: y(t) }));

    return { bars, xTicks, yTicks, x, y, w, h, margin };
  }, [data, width, height]);

  if (!chart) {
    return (
      <div ref={containerRef} style={{ width: "100%", height, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>
        No token data
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
                {formatTokens(t.val)}
              </text>
            </g>
          ))}

          {/* Bars */}
          {chart.bars.map((b) => (
            <g key={b.dateStr}>
              {/* Input (bottom) */}
              <rect
                x={b.x}
                y={b.input.y}
                width={b.barWidth}
                height={Math.max(b.input.height, 0)}
                fill={SERIES[0].color}
                opacity={0.85}
                rx={1}
              >
                <title>{`${d3.timeFormat("%b %d")(b.date)}\nInput: ${formatTokens(b.input.value)}\nOutput: ${formatTokens(b.output.value)}\nTotal: ${formatTokens(b.total)}`}</title>
              </rect>
              {/* Output (top) */}
              <rect
                x={b.x}
                y={b.output.y}
                width={b.barWidth}
                height={Math.max(b.output.height, 0)}
                fill={SERIES[1].color}
                opacity={0.85}
                rx={1}
              >
                <title>{`${d3.timeFormat("%b %d")(b.date)}\nInput: ${formatTokens(b.input.value)}\nOutput: ${formatTokens(b.output.value)}\nTotal: ${formatTokens(b.total)}`}</title>
              </rect>
            </g>
          ))}

          {/* X axis */}
          {chart.xTicks.map((t) => (
            <text
              key={t.toISOString()}
              x={(chart.x(t) || 0) + chart.x.bandwidth() / 2}
              y={chart.h + 18}
              fontSize={10}
              fill="rgba(255,255,255,0.4)"
              textAnchor="middle"
            >
              {d3.timeFormat("%b %d")(t)}
            </text>
          ))}

          {/* Legend */}
          <g transform={`translate(${chart.w + 12}, 0)`}>
            {SERIES.map((s, i) => (
              <g key={s.key} transform={`translate(0,${i * 20})`}>
                <rect x={0} y={1} width={12} height={12} fill={s.color} opacity={0.85} rx={2} />
                <text x={18} y={11} fontSize={11} fill="rgba(255,255,255,0.6)">{s.label}</text>
              </g>
            ))}
          </g>
        </g>
      </svg>
    </div>
  );
}
