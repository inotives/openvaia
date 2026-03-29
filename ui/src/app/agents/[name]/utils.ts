import React from "react";
import {
  BulbOutlined,
  CloudServerOutlined,
  CodeOutlined,
  DatabaseOutlined,
  EditOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  GlobalOutlined,
  MessageOutlined,
  RobotOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import type { RadarDatum } from "@/components/charts/CircularBarplot";

/* ── Interfaces ── */

export interface AgentMetrics {
  role: string;
  radar: RadarDatum[];
  tasksByStatus: Record<string, number>;
  tasksByPriority: { priority: string; status: string; count: number }[];
  messageCounts: { space: string; count: number }[];
  memoryCounts: { tier: string; count: number }[];
  researchCount: number;
  conversationCount: number;
  repoCount: number;
  healthHistory: { checked_at: string; details: any }[];
  activityTimeline: { date: string; tasks_created: number; tasks_completed: number; messages_sent: number }[];
  completionHeatmap: { date: string; count: number }[];
  tokenUsage: { input: number; output: number; total: number };
  tokenTimeline: { date: string; input_tokens: number; output_tokens: number }[];
  systemPromptTokens: number;
}

export interface Repo {
  id: number;
  repo_url: string;
  repo_name: string;
  assigned_by: string | null;
  created_at: string;
}

export interface ResearchReport {
  id: number;
  task_key: string | null;
  title: string;
  summary: string;
  body?: string;
  tags: string[];
  created_at: string;
}

/* ── Skill helpers ── */

export const SKILL_ICON_MAP: Record<string, React.ReactNode> = {
  code: React.createElement(CodeOutlined),
  coding: React.createElement(CodeOutlined),
  dev: React.createElement(CodeOutlined),
  search: React.createElement(SearchOutlined),
  research: React.createElement(FileSearchOutlined),
  browse: React.createElement(GlobalOutlined),
  browser: React.createElement(GlobalOutlined),
  web: React.createElement(GlobalOutlined),
  chat: React.createElement(MessageOutlined),
  message: React.createElement(MessageOutlined),
  discord: React.createElement(MessageOutlined),
  data: React.createElement(DatabaseOutlined),
  database: React.createElement(DatabaseOutlined),
  memory: React.createElement(DatabaseOutlined),
  deploy: React.createElement(CloudServerOutlined),
  server: React.createElement(CloudServerOutlined),
  api: React.createElement(CloudServerOutlined),
  write: React.createElement(EditOutlined),
  report: React.createElement(FileTextOutlined),
  doc: React.createElement(FileTextOutlined),
  think: React.createElement(BulbOutlined),
  plan: React.createElement(BulbOutlined),
  analyze: React.createElement(ExperimentOutlined),
  test: React.createElement(ExperimentOutlined),
  auto: React.createElement(RobotOutlined),
  agent: React.createElement(RobotOutlined),
  tool: React.createElement(ToolOutlined),
  shell: React.createElement(ToolOutlined),
};

export const SKILL_COLORS = ["#1677ff", "#36cfc9", "#9254de", "#f5222d", "#fa8c16", "#52c41a", "#eb2f96", "#faad14"];

export function getSkillIcon(skill: any): React.ReactNode {
  const text = `${skill.name} ${(skill.tags || []).join(" ")} ${skill.description || ""}`.toLowerCase();
  for (const [keyword, icon] of Object.entries(SKILL_ICON_MAP)) {
    if (text.includes(keyword)) return icon;
  }
  return React.createElement(ThunderboltOutlined);
}

export function getSkillColor(skill: any): string {
  let hash = 0;
  for (let i = 0; i < skill.name.length; i++) hash = skill.name.charCodeAt(i) + ((hash << 5) - hash);
  return SKILL_COLORS[Math.abs(hash) % SKILL_COLORS.length];
}

export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "\u2014";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
