"use client";

import React, { useCallback, useEffect, useState } from "react";

interface AgentMetrics {
  role: string;
  tasksByStatus: Record<string, number>;
  memoryCounts: { tier: string; count: number }[];
  researchCount: number;
  conversationCount: number;
  tokenUsage: { total: number };
  systemPromptTokens: number;
}

interface Props {
  name: string;
  isMobile: boolean;
  onClose: () => void;
}

type Tab = "profile" | "chat" | "skills" | "research" | "memory";

export default function AgentPanel({ name, isMobile, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("profile");
  const [metrics, setMetrics] = useState<AgentMetrics | null>(null);
  const [skills, setSkills] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);
  const [research, setResearch] = useState<any[]>([]);
  const [selectedReport, setSelectedReport] = useState<any>(null);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [loading, setLoading] = useState(false);
  // Stable session ID per agent per day — persists across panel open/close
  const [chatSession] = useState(() => {
    const day = new Date().toISOString().slice(0, 10);
    return `${name}-${day}`;
  });

  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch(`/api/agents/${name}/metrics`);
      const data = await res.json();
      if (!data.error) setMetrics(data);
    } catch {}
  }, [name]);

  const fetchSkills = useCallback(async () => {
    try {
      const [agentRes, allRes] = await Promise.all([
        fetch(`/api/agents/${name}/skills`),
        fetch(`/api/skills`),
      ]);
      const agentData = await agentRes.json();
      const allData = await allRes.json();
      if (!agentData.error && !allData.error) {
        const equippedIds = new Set(agentData.map((s: any) => s.id));
        const merged = allData
          .filter((s: any) => s.enabled)
          .map((s: any) => ({ ...s, equipped: s.global || equippedIds.has(s.id) }));
        setSkills(merged);
      }
    } catch {}
  }, [name]);

  const fetchMemories = useCallback(async () => {
    try {
      const res = await fetch(`/api/agents/${name}/memories?limit=20`);
      const data = await res.json();
      if (!data.error) setMemories(data);
    } catch {}
  }, [name]);

  const fetchResearch = useCallback(async () => {
    try {
      const res = await fetch(`/api/agents/${name}/research`);
      const data = await res.json();
      if (!data.error) setResearch(data);
    } catch {}
  }, [name]);

  const fetchReport = useCallback(async (id: number) => {
    try {
      const res = await fetch(`/api/agents/${name}/research/${id}`);
      const data = await res.json();
      if (!data.error) setSelectedReport(data);
    } catch {}
  }, [name]);

  const fetchChat = useCallback(async () => {
    try {
      const res = await fetch(`/api/agents/${name}/chat?session=${chatSession}`);
      const data = await res.json();
      if (!data.error) setChatMessages(data.messages || []);
    } catch {}
  }, [name, chatSession]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      if (tab === "skills") await fetchSkills();
      if (tab === "research") { await fetchResearch(); setSelectedReport(null); }
      if (tab === "memory") await fetchMemories();
      if (tab === "chat") await fetchChat();
      setLoading(false);
    };
    load();
  }, [tab, fetchSkills, fetchResearch, fetchMemories, fetchChat]);

  const sendChat = async () => {
    if (!chatInput.trim() || chatSending) return;
    setChatSending(true);
    try {
      await fetch(`/api/agents/${name}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: chatInput.trim(), session: chatSession }),
      });
      setChatInput("");
      setTimeout(fetchChat, 1000);
    } catch {} finally {
      setChatSending(false);
    }
  };

  // Auto-poll chat every 3 seconds when on chat tab
  useEffect(() => {
    if (tab !== "chat") return;
    const interval = setInterval(fetchChat, 3000);
    return () => clearInterval(interval);
  }, [tab, fetchChat]);

  const totalTasks = metrics ? Object.values(metrics.tasksByStatus).reduce((a, b) => a + b, 0) : 0;
  const totalMemories = metrics?.memoryCounts.reduce((a, r) => a + r.count, 0) ?? 0;

  const panelStyle: React.CSSProperties = isMobile
    ? { position: "fixed", bottom: 0, left: 0, right: 0, height: "60vh", zIndex: 20 }
    : { position: "fixed", top: 40, right: 0, width: 360, height: "calc(100vh - 40px)", zIndex: 20 };

  return (
    <div style={{
      ...panelStyle,
      backgroundColor: "#1a1a2e",
      border: "2px solid #4ade80",
      display: "flex",
      flexDirection: "column",
      fontFamily: "'Pixelify Sans', sans-serif",
      color: "#e0e0e0",
    }}>
      {/* Title bar */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "8px 12px",
        borderBottom: "2px solid #333",
        backgroundColor: "#222244",
      }}>
        <span style={{ color: "#4ade80", fontSize: 14 }}>
          ◆ {name}
        </span>
        <button onClick={onClose} style={{
          background: "none",
          border: "1px solid #666",
          color: "#ff6666",
          cursor: "pointer",
          fontFamily: "'Pixelify Sans', sans-serif",
          fontSize: 12,
          padding: "2px 8px",
        }}>
          ✕
        </button>
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex",
        borderBottom: "2px solid #333",
      }}>
        {(["profile", "chat", "skills", "research", "memory"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1,
            padding: "8px 4px",
            background: tab === t ? "#333355" : "transparent",
            border: "none",
            borderRight: "1px solid #333",
            color: tab === t ? "#4ade80" : "#888",
            cursor: "pointer",
            fontFamily: "'Pixelify Sans', sans-serif",
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: 1,
          }}>
            {t}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", padding: 12 }}>
        {loading && tab !== "profile" && (
          <div style={{ color: "#666", fontSize: 11, textAlign: "center", marginTop: 20, fontFamily: "Pixelify Sans, monospace" }}>
            Loading ...
          </div>
        )}
        {tab === "profile" && (
          <ProfileTab name={name} metrics={metrics} totalTasks={totalTasks} totalMemories={totalMemories} />
        )}
        {tab === "chat" && (
          <ChatTab
            name={name}
            messages={chatMessages}
            input={chatInput}
            sending={chatSending}
            onInputChange={setChatInput}
            onSend={sendChat}
            onRefresh={fetchChat}
          />
        )}
        {tab === "skills" && (
          <SkillsTab name={name} skills={skills} onRefresh={fetchSkills} />
        )}
        {tab === "research" && (
          <ResearchTab reports={research} selectedReport={selectedReport} onSelect={fetchReport} onBack={() => setSelectedReport(null)} />
        )}
        {tab === "memory" && (
          <MemoryTab memories={memories} />
        )}
      </div>
    </div>
  );
}

// --- Sub-components ---

function ProfileTab({ name, metrics, totalTasks, totalMemories }: {
  name: string;
  metrics: AgentMetrics | null;
  totalTasks: number;
  totalMemories: number;
}) {
  return (
    <div>
      <div style={{ textAlign: "center", marginBottom: 16 }}>
        {/* Pixel avatar placeholder */}
        <div style={{
          width: 64, height: 64,
          margin: "0 auto 8px",
          backgroundColor: "#333355",
          border: "2px solid #4ade80",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 28,
        }}>
          {name === "ino" ? "🔬" : name === "robin" ? "🔧" : "🤖"}
        </div>
        <div style={{ fontSize: 16, color: "#4ade80" }}>{name}</div>
        <div style={{ fontSize: 11, color: "#888" }}>{metrics?.role || "Agent"}</div>
      </div>

      {/* Stats bars */}
      <StatBar label="Tasks" value={totalTasks} max={50} color="#4488ff" />
      <StatBar label="Memories" value={totalMemories} max={100} color="#44bb66" />
      <StatBar label="Research" value={metrics?.researchCount ?? 0} max={20} color="#ff8844" />
      <StatBar label="Convos" value={metrics?.conversationCount ?? 0} max={50} color="#bb44ff" />

      {/* Token usage */}
      <div style={{ marginTop: 16, fontSize: 11, color: "#888" }}>
        <div>Tokens (24h): {formatNum(metrics?.tokenUsage?.total ?? 0)}</div>
        <div>Sys Prompt: {formatNum(metrics?.systemPromptTokens ?? 0)} tokens</div>
      </div>

      {/* Task breakdown */}
      {metrics && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 12, color: "#aaa", marginBottom: 8 }}>Tasks</div>
          {Object.entries(metrics.tasksByStatus).map(([status, count]) => (
            count > 0 && (
              <div key={status} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#888", marginBottom: 4 }}>
                <span>{status}</span>
                <span style={{ color: "#fff" }}>{count}</span>
              </div>
            )
          ))}
        </div>
      )}
    </div>
  );
}

function StatBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 2 }}>
        <span style={{ color: "#aaa" }}>{label}</span>
        <span style={{ color: "#fff" }}>{value}</span>
      </div>
      <div style={{ height: 8, backgroundColor: "#222", border: "1px solid #444" }}>
        <div style={{ height: "100%", width: `${pct}%`, backgroundColor: color, transition: "width 0.3s" }} />
      </div>
    </div>
  );
}

function ChatTab({ name, messages, input, sending, onInputChange, onSend, onRefresh }: {
  name: string;
  messages: any[];
  input: string;
  sending: boolean;
  onInputChange: (v: string) => void;
  onSend: () => void;
  onRefresh: () => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, overflow: "auto", marginBottom: 8 }}>
        {messages.length === 0 && (
          <div style={{ color: "#666", fontSize: 11, textAlign: "center", marginTop: 20 }}>
            No messages yet. Say something!
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{
            marginBottom: 8,
            padding: "6px 8px",
            backgroundColor: msg.role === "user" ? "#1a3a5c" : "#2a2a3e",
            border: `1px solid ${msg.role === "user" ? "#2a5a8c" : "#3a3a4e"}`,
            fontSize: 11,
            lineHeight: 1.5,
            wordBreak: "break-word",
          }}>
            <div style={{ color: msg.role === "user" ? "#4ade80" : "#ff8844", fontSize: 10, marginBottom: 2 }}>
              {msg.role === "user" ? "YOU" : name.toUpperCase()}
            </div>
            {msg.content}
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 4 }}>
        <input
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSend()}
          placeholder="Type a message..."
          disabled={sending}
          style={{
            flex: 1,
            padding: "6px 8px",
            backgroundColor: "#222",
            border: "1px solid #444",
            color: "#e0e0e0",
            fontFamily: "'Pixelify Sans', sans-serif",
            fontSize: 11,
            outline: "none",
          }}
        />
        <button onClick={onSend} disabled={sending} style={{
          padding: "6px 12px",
          backgroundColor: "#4ade80",
          border: "none",
          color: "#1a1a2e",
          cursor: "pointer",
          fontFamily: "'Pixelify Sans', sans-serif",
          fontSize: 11,
          fontWeight: "bold",
        }}>
          {sending ? "..." : "SEND"}
        </button>
        <button onClick={onRefresh} style={{
          padding: "6px 8px",
          backgroundColor: "transparent",
          border: "1px solid #444",
          color: "#888",
          cursor: "pointer",
          fontFamily: "'Pixelify Sans', sans-serif",
          fontSize: 11,
        }}>
          ↻
        </button>
      </div>
    </div>
  );
}

function SkillsTab({ name, skills, onRefresh }: { name: string; skills: any[]; onRefresh: () => void }) {
  const [toggling, setToggling] = useState<number | null>(null);

  const toggleSkill = async (skill: any) => {
    setToggling(skill.id);
    try {
      if (skill.equipped) {
        await fetch(`/api/agents/${name}/skills`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skill_id: skill.id }),
        });
      } else {
        await fetch(`/api/agents/${name}/skills`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skill_id: skill.id }),
        });
      }
      onRefresh();
    } catch {} finally {
      setToggling(null);
    }
  };

  const equipped = skills.filter(s => s.equipped);
  const available = skills.filter(s => !s.equipped);

  return (
    <div>
      <div style={{ fontSize: 10, color: "#888", marginBottom: 6 }}>
        {equipped.length} equipped · {available.length} available
      </div>
      {skills.length === 0 && (
        <div style={{ color: "#666", fontSize: 11, textAlign: "center", marginTop: 20 }}>
          No skills found
        </div>
      )}
      {skills.map((skill) => (
        <div key={skill.id} style={{
          marginBottom: 6,
          padding: "6px 8px",
          backgroundColor: skill.equipped ? "#1a2a3e" : "#1e1e2a",
          border: `1px solid ${skill.equipped ? "#2a4a6e" : "#2a2a3a"}`,
          opacity: skill.equipped ? 1 : 0.7,
          display: "flex",
          alignItems: "flex-start",
          gap: 8,
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, color: skill.equipped ? "#4ade80" : "#888" }}>
              {skill.name}
              {skill.global && (
                <span style={{ fontSize: 9, color: "#666", marginLeft: 6 }}>GLOBAL</span>
              )}
            </div>
            <div style={{ fontSize: 10, color: "#666", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {skill.description}
            </div>
          </div>
          {!skill.global && (
            <button
              onClick={() => toggleSkill(skill)}
              disabled={toggling === skill.id}
              style={{
                fontFamily: "Pixelify Sans, monospace",
                fontSize: 9,
                padding: "2px 8px",
                border: `1px solid ${skill.equipped ? "#cc4444" : "#4ade80"}`,
                backgroundColor: "transparent",
                color: skill.equipped ? "#cc4444" : "#4ade80",
                cursor: toggling === skill.id ? "wait" : "pointer",
                flexShrink: 0,
                marginTop: 2,
              }}
            >
              {toggling === skill.id ? "..." : skill.equipped ? "UNEQUIP" : "EQUIP"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function ResearchTab({ reports, selectedReport, onSelect, onBack }: {
  reports: any[]; selectedReport: any; onSelect: (id: number) => void; onBack: () => void;
}) {
  if (selectedReport) {
    return (
      <div>
        <button onClick={onBack} style={{
          fontFamily: "Pixelify Sans, monospace", fontSize: 10, padding: "2px 8px",
          border: "1px solid #555", backgroundColor: "transparent", color: "#888",
          cursor: "pointer", marginBottom: 8,
        }}>
          ← BACK
        </button>
        <div style={{ fontSize: 13, color: "#4ade80", marginBottom: 4 }}>{selectedReport.title}</div>
        {selectedReport.tags?.length > 0 && (
          <div style={{ marginBottom: 6 }}>
            {selectedReport.tags.map((t: string) => (
              <span key={t} style={{
                display: "inline-block", fontSize: 9, color: "#aaa", backgroundColor: "#333",
                padding: "1px 6px", marginRight: 4, border: "1px solid #444",
              }}>{t}</span>
            ))}
          </div>
        )}
        <div style={{ fontSize: 10, color: "#666", marginBottom: 8 }}>
          {new Date(selectedReport.created_at).toLocaleString()}
        </div>
        {selectedReport.summary && (
          <div style={{ fontSize: 11, color: "#aaa", marginBottom: 8, padding: "6px 8px", backgroundColor: "#1a2a3e", border: "1px solid #2a4a6e" }}>
            {selectedReport.summary}
          </div>
        )}
        <div style={{
          fontSize: 11, color: "#ccc", lineHeight: 1.6, whiteSpace: "pre-wrap", wordBreak: "break-word",
        }}>
          {selectedReport.body}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ fontSize: 10, color: "#888", marginBottom: 6 }}>
        {reports.length} report{reports.length !== 1 ? "s" : ""}
      </div>
      {reports.length === 0 && (
        <div style={{ color: "#666", fontSize: 11, textAlign: "center", marginTop: 20 }}>
          No research reports
        </div>
      )}
      {reports.map((r) => (
        <div key={r.id} onClick={() => onSelect(r.id)} style={{
          marginBottom: 6, padding: "6px 8px", backgroundColor: "#1e1e2a",
          border: "1px solid #2a2a3a", cursor: "pointer",
        }}>
          <div style={{ fontSize: 12, color: "#4ade80" }}>{r.title}</div>
          {r.summary && (
            <div style={{ fontSize: 10, color: "#888", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {r.summary}
            </div>
          )}
          <div style={{ fontSize: 9, color: "#555", marginTop: 4 }}>
            {new Date(r.created_at).toLocaleString()}
            {r.tags?.length > 0 && ` · ${r.tags.join(", ")}`}
          </div>
        </div>
      ))}
    </div>
  );
}

function MemoryTab({ memories }: { memories: any[] }) {
  return (
    <div>
      {memories.length === 0 && (
        <div style={{ color: "#666", fontSize: 11, textAlign: "center", marginTop: 20 }}>
          No memories stored
        </div>
      )}
      {memories.map((mem) => (
        <div key={mem.id} style={{
          marginBottom: 8,
          padding: "6px 8px",
          backgroundColor: "#2a2a3e",
          border: `1px solid ${mem.tier === "long" ? "#4488ff" : "#3a3a4e"}`,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{
              fontSize: 9,
              color: mem.tier === "long" ? "#4488ff" : "#888",
              border: `1px solid ${mem.tier === "long" ? "#4488ff" : "#444"}`,
              padding: "0 4px",
            }}>
              {mem.tier}
            </span>
            <span style={{ fontSize: 9, color: "#666" }}>
              {new Date(mem.created_at).toLocaleDateString()}
            </span>
          </div>
          <div style={{ fontSize: 11, color: "#ccc", lineHeight: 1.4 }}>
            {mem.content.length > 150 ? mem.content.slice(0, 150) + "..." : mem.content}
          </div>
          <div style={{ marginTop: 4 }}>
            {(mem.tags || []).map((t: string) => (
              <span key={t} style={{
                display: "inline-block",
                fontSize: 9,
                color: "#aaa",
                backgroundColor: "#333",
                padding: "1px 6px",
                marginRight: 4,
                border: "1px solid #444",
              }}>
                {t}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function formatNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
