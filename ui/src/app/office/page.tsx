"use client";

import React, { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";

// PixiJS must be loaded client-side only (no SSR)
const OfficeCanvas = dynamic(() => import("./components/OfficeCanvas"), { ssr: false });
const AgentPanel = dynamic(() => import("./components/AgentPanel"), { ssr: false });

interface AgentData {
  name: string;
  role: string;
  status: string;
  healthy: boolean | null;
  last_seen: string | null;
  skill_count: number;
}

/** Map agent activity to room IDs based on tasks + recent chat activity */
function activityToRoom(tasks: any[], recentChat: string, isBusy: boolean): string {
  // Check in-progress tasks first
  const active = tasks.find((t: any) => t.status === "in_progress");
  if (active) {
    const combined = `${active.title || ""} ${(active.tags || []).join(" ")}`.toLowerCase();
    if (combined.includes("research") || combined.includes("search") || combined.includes("analyze")) return "f1_research";
    if (combined.includes("trad") || combined.includes("market") || combined.includes("price")) return "f2_trading";
    return "f2_office";
  }

  // If busy (processing chat), check recent conversation content
  if (isBusy && recentChat) {
    const chat = recentChat.toLowerCase();
    if (chat.includes("research") || chat.includes("search") || chat.includes("analyze") || chat.includes("find")) return "f1_research";
    if (chat.includes("trad") || chat.includes("market") || chat.includes("price") || chat.includes("crypto") || chat.includes("gold")) return "f2_trading";
    return "f2_office";
  }

  return "f1_resting";
}

export default function OfficePage() {
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [agentRooms, setAgentRooms] = useState<Record<string, string>>({});
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch("/api/dashboard/agents");
      const data = await res.json();
      if (!data.error) setAgents(data);
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    }
  }, []);

  const fetchAgentRooms = useCallback(async (agentList: AgentData[]) => {
    const rooms: Record<string, string> = {};
    // Get busy status from the full agent details
    let busyMap: Record<string, boolean> = {};
    try {
      const res = await fetch("/api/dashboard/agents");
      const data = await res.json();
      if (Array.isArray(data)) {
        data.forEach((a: any) => { busyMap[a.name] = a.details?.is_busy || false; });
      }
    } catch {}

    await Promise.all(agentList.map(async (a) => {
      try {
        const [taskRes, chatRes] = await Promise.all([
          fetch(`/api/tasks?assigned_to=${a.name}&status=in_progress`),
          fetch(`/api/agents/${a.name}/chat?session=${a.name}-${new Date().toISOString().slice(0, 10)}`),
        ]);
        const tasks = await taskRes.json();
        const chatData = await chatRes.json();
        const messages = chatData.messages || [];
        const lastUserMsg = [...messages].reverse().find((m: any) => m.role === "user");
        const recentChat = lastUserMsg?.content || "";
        const isBusy = busyMap[a.name] || false;
        rooms[a.name] = activityToRoom(Array.isArray(tasks) ? tasks : [], recentChat, isBusy);
      } catch {
        rooms[a.name] = "f1_resting";
      }
    }));
    setAgentRooms(rooms);
  }, []);

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 15000);
    return () => clearInterval(interval);
  }, [fetchAgents]);

  useEffect(() => {
    if (agents.length > 0) fetchAgentRooms(agents);
    const interval = setInterval(() => fetchAgentRooms(agents), 10000);
    return () => clearInterval(interval);
  }, [agents, fetchAgentRooms]);

  return (
    <div style={{
      width: "100vw",
      height: "100vh",
      overflow: "hidden",
      position: "relative",
      backgroundColor: "#1a1a2e",
      fontFamily: "'Pixelify Sans', sans-serif",
    }}>
      {/* Office title bar */}
      <div style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: 40,
        backgroundColor: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        zIndex: 10,
        borderBottom: "2px solid #333",
      }}>
        <span style={{ color: "#4ade80", fontSize: 14, letterSpacing: 1 }}>
          OpenVAIA Office
        </span>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {agents.map((a) => (
            <span key={a.name} style={{
              color: a.status === "online" ? "#4ade80" : "#666",
              fontSize: 11,
              cursor: "pointer",
            }} onClick={() => setSelectedAgent(a.name)}>
              ● {a.name}
            </span>
          ))}
          <a href="/dashboard" style={{ color: "#888", fontSize: 11, textDecoration: "none" }}>
            [Admin UI]
          </a>
        </div>
      </div>

      {/* PixiJS Canvas */}
      <OfficeCanvas
        agents={agents}
        agentRooms={agentRooms}
        selectedAgent={selectedAgent}
        onSelectAgent={setSelectedAgent}
      />

      {/* Agent interaction panel */}
      {selectedAgent && (
        <AgentPanel
          name={selectedAgent}
          isMobile={isMobile}
          onClose={() => setSelectedAgent(null)}
        />
      )}
    </div>
  );
}
