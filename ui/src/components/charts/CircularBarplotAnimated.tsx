"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";

interface BarDatum {
  id: number;
  category: string;
  value: number;
  color: string;
}

const CATEGORIES = [
  { name: "Tasks", color: "#00d2ff" },
  { name: "Done", color: "#52c41a" },
  { name: "In Progress", color: "#fadb14" },
  { name: "Messages", color: "#ff6eb4" },
  { name: "Memories", color: "#b37feb" },
  { name: "Research", color: "#00d2ff" },
  { name: "Conversations", color: "#ff6eb4" },
  { name: "Repos", color: "#8c8c8c" },
];

// Scale bar count based on size — fewer bars for small renders
function getBarsPerCategory(size: number): number {
  if (size <= 100) return 3;
  if (size <= 200) return 6;
  return 15;
}

function generateData(barsPerCategory: number): BarDatum[] {
  const total = CATEGORIES.length * barsPerCategory;
  return Array.from({ length: total }, (_, i) => {
    const cat = CATEGORIES[Math.floor(i / barsPerCategory)];
    return {
      id: i,
      category: cat.name,
      value: Math.floor(Math.random() * 100) + 1,
      color: cat.color,
    };
  });
}

interface Props {
  size?: number;
  label?: string;
}

export default function CircularBarplotAnimated({ size = 500, label }: Props) {
  const [mounted, setMounted] = useState(false);
  const barsPerCategory = useMemo(() => getBarsPerCategory(size), [size]);
  const [data, setData] = useState<BarDatum[]>(() => generateData(barsPerCategory));
  const prevDataRef = useRef<BarDatum[]>(data);
  const progressRef = useRef(1);
  const isSmall = size <= 200;

  useEffect(() => { setMounted(true); }, []);

  // Regenerate data — slower interval for small sizes
  useEffect(() => {
    const interval = setInterval(() => {
      prevDataRef.current = data;
      progressRef.current = 0;
      setData(generateData(barsPerCategory));
    }, isSmall ? 8000 : 5000);
    return () => clearInterval(interval);
  }, [data, barsPerCategory, isSmall]);

  // Animation frame loop
  const [, forceRender] = useState(0);
  useEffect(() => {
    let raf: number;
    const startTime = performance.now();
    const duration = 600;

    const tick = (now: number) => {
      const elapsed = now - startTime;
      progressRef.current = Math.min(elapsed / duration, 1);
      const t = progressRef.current;
      progressRef.current = 1 - Math.pow(1 - t, 3);
      forceRender((n) => n + 1);
      if (t < 1) {
        raf = requestAnimationFrame(tick);
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [data]);

  const progress = progressRef.current;
  const prevData = prevDataRef.current;

  const chart = useMemo(() => {
    const scale = size / 500;
    const margin = Math.round(70 * scale);
    const innerRadius = Math.round(40 * scale);
    const outerRadius = size / 2 - margin;

    const xScale = d3
      .scaleBand()
      .domain(data.map((_, i) => String(i)))
      .range([0, 2 * Math.PI])
      .padding(isSmall ? 0.12 : 0.08);

    const yScale = d3.scaleRadial().domain([0, 100]).range([innerRadius, outerRadius]);

    const bars = data.map((d, i) => {
      const prevVal = prevData[i]?.value ?? d.value;
      const currentVal = prevVal + (d.value - prevVal) * progress;

      const startAngle = xScale(String(i)) || 0;
      const endAngle = startAngle + (xScale.bandwidth() || 0);

      const arcPath = d3.arc()({
        innerRadius,
        outerRadius: yScale(currentVal),
        startAngle,
        endAngle,
      } as any);

      return {
        ...d,
        interpolatedValue: currentVal,
        path: arcPath || "",
      };
    });

    return { bars, innerRadius };
  }, [data, prevData, progress, size, isSmall]);

  const cx = size / 2;
  const cy = size / 2;

  if (!mounted) return <div style={{ width: size, height: size }} />;

  return (
    <svg
      width={size}
      height={size}
      style={{ background: "transparent", borderRadius: 12, overflow: "visible" }}
    >
      <g transform={`translate(${cx},${cy})`}>
        {/* Inner dark circle */}
        <circle r={chart.innerRadius} fill="#16162a" stroke="rgba(255,255,255,0.1)" strokeWidth={1} />

        {/* Center letter */}
        <text
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={Math.round(28 * size / 500)}
          fontWeight={700}
          fill="rgba(255,255,255,0.8)"
          style={{ fontFamily: "monospace" }}
        >
          {label ? label.charAt(0).toUpperCase() : ""}
        </text>

        {/* Bars — no blur filter for small sizes */}
        {chart.bars.map((b) => (
          <path
            key={b.id}
            d={b.path}
            fill={b.color}
            opacity={0.8}
          />
        ))}
      </g>
    </svg>
  );
}
