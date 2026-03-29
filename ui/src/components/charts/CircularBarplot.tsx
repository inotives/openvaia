"use client";

import React, { useMemo, useState } from "react";
import * as d3 from "d3";

export interface RadarDatum {
  category: string;
  value: number;
  color: string;
}

interface Props {
  data: RadarDatum[];
  size?: number;
  hideLabels?: boolean;
}

export default function CircularBarplot({ data, size = 400, hideLabels = false }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);

  const chart = useMemo(() => {
    if (!data.length) return null;

    const margin = 60;
    const innerRadius = 50;
    const outerRadius = size / 2 - margin;

    const maxVal = Math.max(...data.map((d) => d.value), 1);

    const xScale = d3
      .scaleBand()
      .domain(data.map((d) => d.category))
      .range([0, 2 * Math.PI])
      .padding(0.15);

    const yScale = d3
      .scaleRadial()
      .domain([0, maxVal])
      .range([innerRadius, outerRadius]);

    const arcGen = d3.arc<RadarDatum>();

    const bars = data.map((d) => {
      const startAngle = xScale(d.category) || 0;
      const endAngle = startAngle + (xScale.bandwidth() || 0);

      const path = arcGen({
        innerRadius,
        outerRadius: yScale(d.value),
        startAngle,
        endAngle,
        data: d,
        index: 0,
        value: d.value,
        padAngle: 0,
      } as any);

      // Label position — outside the bar
      const labelAngle = (startAngle + endAngle) / 2;
      const labelRadius = outerRadius + 16;
      const labelX = labelRadius * Math.sin(labelAngle);
      const labelY = -labelRadius * Math.cos(labelAngle);
      const rotation = (labelAngle * 180) / Math.PI;
      const flip = rotation > 90 && rotation < 270;

      // Value position — at the tip of the bar
      const valRadius = yScale(d.value) + 10;
      const valX = valRadius * Math.sin(labelAngle);
      const valY = -valRadius * Math.cos(labelAngle);

      return { ...d, path, labelX, labelY, rotation, flip, valX, valY };
    });

    return { bars, innerRadius };
  }, [data, size]);

  if (!chart) {
    return (
      <div style={{ width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>
        No data
      </div>
    );
  }

  const cx = size / 2;
  const cy = size / 2;

  return (
    <svg width={size} height={size} style={{ overflow: "visible" }}>
      <defs>
        <filter id="radarGlow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <g transform={`translate(${cx},${cy})`}>
        {/* Inner circle */}
        <circle r={chart.innerRadius} fill="#fafafa" stroke="#e8e8e8" />

        {/* Bars */}
        {chart.bars.map((b) => {
          const isHovered = hovered === b.category;
          const isDimmed = hovered !== null && !isHovered;

          return (
            <g
              key={b.category}
              onMouseEnter={() => setHovered(b.category)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: "pointer" }}
            >
              <path
                d={b.path || ""}
                fill={b.color}
                opacity={isDimmed ? 0.25 : 0.85}
                stroke={b.color}
                strokeWidth={isHovered ? 1.5 : 0.5}
                filter={isHovered ? "url(#radarGlow)" : undefined}
                style={{
                  transition: "opacity 0.2s, stroke-width 0.2s, transform 0.2s",
                  transformOrigin: "0px 0px",
                  transform: isHovered ? "scale(1.06)" : "scale(1)",
                }}
              />

              {/* Value at tip */}
              {b.value > 0 && (
                <text
                  x={b.valX}
                  y={b.valY}
                  fontSize={isHovered ? 14 : 11}
                  fontWeight={isHovered ? 700 : 600}
                  fill={b.color}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  opacity={isDimmed ? 0.3 : 1}
                  style={{ transition: "font-size 0.2s, opacity 0.2s" }}
                >
                  {b.value}
                </text>
              )}

              {/* Category label */}
              {!hideLabels && (
                <text
                  transform={`translate(${b.labelX},${b.labelY}) rotate(${b.flip ? b.rotation - 180 : b.rotation})`}
                  fontSize={isHovered ? 13 : 11}
                  fontWeight={isHovered ? 600 : 400}
                  fill={isDimmed ? "#999" : "#595959"}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  style={{ transition: "font-size 0.2s, fill 0.2s" }}
                >
                  {b.category}
                </text>
              )}
            </g>
          );
        })}

        {/* Center label */}
        <text
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={13}
          fontWeight={600}
          fill="#262626"
        >
          {hovered ?? "Activity"}
        </text>
      </g>
    </svg>
  );
}
