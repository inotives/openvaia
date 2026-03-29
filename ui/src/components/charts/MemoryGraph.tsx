"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";

interface Memory {
  id: number;
  content: string;
  tags: string[];
  tier: string;
  created_at: string;
}

interface Props {
  data: Memory[];
  height?: number;
  onNodeClick?: (memory: Memory) => void;
}

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  type: "memory" | "tag";
  label: string;
  memory?: Memory;
  radius: number;
  color: string;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
}

const TIER_COLORS = {
  long: "#1677ff",
  short: "#8c8c8c",
};

const TAG_COLOR = "#36cfc9";

function buildGraph(memories: Memory[]): { nodes: GraphNode[]; links: GraphLink[] } {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  const tagSet = new Set<string>();

  // Create memory nodes
  for (const mem of memories) {
    const contentLen = mem.content.length;
    const radius = Math.max(6, Math.min(18, 6 + Math.sqrt(contentLen / 10)));
    nodes.push({
      id: `mem-${mem.id}`,
      type: "memory",
      label: mem.content.slice(0, 60) + (mem.content.length > 60 ? "..." : ""),
      memory: mem,
      radius,
      color: TIER_COLORS[mem.tier as keyof typeof TIER_COLORS] || TIER_COLORS.short,
    });

    for (const tag of mem.tags || []) {
      tagSet.add(tag);
      links.push({ source: `mem-${mem.id}`, target: `tag-${tag}` });
    }
  }

  // Create tag nodes
  for (const tag of tagSet) {
    const count = memories.filter((m) => m.tags?.includes(tag)).length;
    nodes.push({
      id: `tag-${tag}`,
      type: "tag",
      label: tag,
      radius: Math.max(14, Math.min(30, 10 + count * 4)),
      color: TAG_COLOR,
    });
  }

  return { nodes, links };
}

export default function MemoryGraph({ data, height = 500, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [width, setWidth] = useState(800);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; content: string; tier?: string; type: string } | null>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);

  // Responsive width
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 0) setWidth(w);
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // Build and run simulation
  useEffect(() => {
    if (!svgRef.current || !data.length) return;

    const { nodes, links } = buildGraph(data);
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g");

    // Zoom
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
    svg.call(zoom);

    // Simulation
    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force("link", d3.forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(60).strength(0.4))
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide<GraphNode>().radius((d) => d.radius + 4).strength(0.8))
      .force("x", d3.forceX(width / 2).strength(0.04))
      .force("y", d3.forceY(height / 2).strength(0.04));

    simulationRef.current = simulation;

    // Links
    const link = g.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "rgba(255,255,255,0.08)")
      .attr("stroke-width", 1);

    // Node groups
    const node = g.append("g")
      .selectAll<SVGGElement, GraphNode>("g")
      .data(nodes)
      .join("g")
      .style("cursor", (d) => d.type === "memory" ? "pointer" : "default");

    // Shapes: hexagon for tags, triangle for long-term, circle for short-term
    const hexagonPath = (r: number) => {
      const a = Math.PI / 3;
      return Array.from({ length: 6 }, (_, i) =>
        `${r * Math.cos(a * i - Math.PI / 6)},${r * Math.sin(a * i - Math.PI / 6)}`
      ).join(" ");
    };
    const trianglePath = (r: number) => {
      const h = r * 1.3;
      return `0,${-h * 0.7} ${h * 0.65},${h * 0.5} ${-h * 0.65},${h * 0.5}`;
    };

    // Tags → hexagon
    node.filter((d) => d.type === "tag")
      .append("polygon")
      .attr("points", (d) => hexagonPath(d.radius))
      .attr("fill", (d) => d.color)
      .attr("opacity", 0.9)
      .attr("stroke", "rgba(255,255,255,0.3)")
      .attr("stroke-width", 2);

    // Long-term memories → triangle
    node.filter((d) => d.type === "memory" && d.memory?.tier === "long")
      .append("polygon")
      .attr("points", (d) => trianglePath(d.radius))
      .attr("fill", (d) => d.color)
      .attr("opacity", 0.75)
      .attr("stroke", "rgba(255,255,255,0.1)")
      .attr("stroke-width", 1);

    // Short-term memories → circle
    node.filter((d) => d.type === "memory" && d.memory?.tier !== "long")
      .append("circle")
      .attr("r", (d) => d.radius)
      .attr("fill", (d) => d.color)
      .attr("opacity", 0.75)
      .attr("stroke", "rgba(255,255,255,0.1)")
      .attr("stroke-width", 1);


    // Hover
    // Hover — select the shape (circle or polygon) inside the group
    node.on("mouseenter", function (event, d) {
      const el = d3.select(this);
      el.select("circle, polygon")
        .transition().duration(150)
        .attr("opacity", 1)
        .attr("stroke", "rgba(255,255,255,0.6)")
        .attr("stroke-width", 2);

      const rect = svgRef.current!.getBoundingClientRect();
      setTooltip({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top - 10,
        content: d.type === "memory" ? d.memory!.content : `#${d.label}`,
        tier: d.type === "memory" ? d.memory!.tier : undefined,
        type: d.type,
      });
    })
    .on("mouseleave", function (_event, d) {
      const el = d3.select(this);
      el.select("circle, polygon")
        .transition().duration(150)
        .attr("opacity", d.type === "tag" ? 0.9 : 0.75)
        .attr("stroke", d.type === "tag" ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.1)")
        .attr("stroke-width", d.type === "tag" ? 2 : 1);
      setTooltip(null);
    });

    // Click
    node.filter((d) => d.type === "memory")
      .on("click", (_event, d) => {
        if (d.memory && onNodeClick) onNodeClick(d.memory);
      });

    // Drag
    const drag = d3.drag<SVGGElement, GraphNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    node.call(drag);

    // Tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as GraphNode).x!)
        .attr("y1", (d) => (d.source as GraphNode).y!)
        .attr("x2", (d) => (d.target as GraphNode).x!)
        .attr("y2", (d) => (d.target as GraphNode).y!);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [data, width, height, onNodeClick]);

  if (!data.length) {
    return (
      <div ref={containerRef} style={{ width: "100%", height, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>
        No memories to visualize
      </div>
    );
  }

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>
      <svg ref={svgRef} width={width} height={height} style={{ background: "rgba(0,0,0,0.15)", borderRadius: 8 }} />

      {/* Legend */}
      <div style={{ position: "absolute", top: 12, left: 12, display: "flex", gap: 16, fontSize: 11, color: "rgba(255,255,255,0.5)", alignItems: "center" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <svg width={14} height={14}><polygon points="7,1 13,11 1,11" fill={TIER_COLORS.long} /></svg>
          Long-term
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <svg width={12} height={12}><circle cx={6} cy={6} r={5} fill={TIER_COLORS.short} /></svg>
          Short-term
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <svg width={14} height={14}><polygon points="7,1 13,4 12,11 2,11 1,4" fill={TAG_COLOR} /></svg>
          Tag
        </span>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position: "absolute",
          left: tooltip.x,
          top: tooltip.y,
          transform: "translate(-50%, -100%)",
          background: "rgba(0,0,0,0.9)",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 6,
          padding: "8px 12px",
          maxWidth: 320,
          fontSize: 12,
          color: "rgba(255,255,255,0.85)",
          pointerEvents: "none",
          zIndex: 10,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}>
          {tooltip.tier && (
            <div style={{ marginBottom: 4, color: TIER_COLORS[tooltip.tier as keyof typeof TIER_COLORS] || "#999", fontWeight: 600, fontSize: 11, textTransform: "uppercase" }}>
              {tooltip.tier}-term
            </div>
          )}
          {tooltip.content.length > 200 ? tooltip.content.slice(0, 200) + "..." : tooltip.content}
        </div>
      )}
    </div>
  );
}
