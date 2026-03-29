"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Button,
  Card,
  Col,
  Row,
  Space,
  Statistic,
  Tabs,
  Tag,
  Typography,
} from "antd";
import {
  ClockCircleOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  MessageOutlined,
  ReloadOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import CircularBarplotAnimated from "@/components/charts/CircularBarplotAnimated";
import type { Task } from "@/lib/types";
import type { AgentMetrics } from "./utils";
import OverviewTab from "./tabs/OverviewTab";
import ChatTab from "./tabs/ChatTab";
import SkillsTab from "./tabs/SkillsTab";
import ReposTab from "./tabs/ReposTab";
import TasksTab from "./tabs/TasksTab";
import ResearchTab from "./tabs/ResearchTab";
import MemoriesTab from "./tabs/MemoriesTab";
import MemoryGraphTab from "./tabs/MemoryGraphTab";
import SettingsTab from "./tabs/SettingsTab";

const { Title } = Typography;

export default function AgentDetailPage() {
  const { name } = useParams<{ name: string }>();
  const [metrics, setMetrics] = useState<AgentMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  // Tasks state — fetched at page level for stat cards
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [taskFilters, setTaskFilters] = useState<{
    status?: string;
    priority?: string;
    tag?: string;
    search?: string;
    dateRange?: [string, string] | null;
  }>({});

  // Tab label counts (updated by child tabs)
  const [skillCount, setSkillCount] = useState(0);
  const [repoCount, setRepoCount] = useState(0);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/agents/${name}/metrics`);
      const data = await res.json();
      if (!data.error) setMetrics(data);
    } catch (err) {
      console.error("Failed to fetch agent metrics:", err);
    } finally {
      setLoading(false);
    }
  }, [name]);

  const fetchTasks = useCallback(async () => {
    setTasksLoading(true);
    try {
      const params = new URLSearchParams();
      if (taskFilters.status) params.set("status", taskFilters.status);
      if (taskFilters.priority) params.set("priority", taskFilters.priority);
      if (taskFilters.tag) params.set("tag", taskFilters.tag);
      if (taskFilters.search?.trim()) params.set("q", taskFilters.search.trim());
      if (taskFilters.dateRange) {
        params.set("from", taskFilters.dateRange[0]);
        params.set("to", taskFilters.dateRange[1]);
      }
      const res = await fetch(`/api/agents/${name}/tasks?${params}`);
      const data = await res.json();
      if (!data.error) setTasks(data);
    } catch (err) {
      console.error("Failed to fetch tasks:", err);
    } finally {
      setTasksLoading(false);
    }
  }, [name, taskFilters]);

  // Fetch metrics + tasks on mount
  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleRefresh = () => {
    setRefreshKey((k) => k + 1);
    fetchMetrics();
    fetchTasks();
  };

  const handleTaskFiltersChange = useCallback((filters: typeof taskFilters) => {
    setTaskFilters(filters);
  }, []);

  const totalMemories = metrics?.memoryCounts.reduce((a, r) => a + r.count, 0) ?? 0;
  const totalTasks = metrics ? Object.values(metrics.tasksByStatus).reduce((a, b) => a + b, 0) : 0;
  const lastHealth = metrics?.healthHistory.at(-1);

  return (
    <div>
      {/* Header */}
      <Space style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
        <Space>
          <Title level={3} style={{ margin: 0 }}>
            {name}{metrics?.role ? <span style={{ color: "#8c8c8c", fontWeight: 400, fontSize: "0.7em", marginLeft: 8 }}>({metrics.role})</span> : null}
          </Title>
          {lastHealth && (
            !lastHealth.checked_at || (Date.now() - new Date(lastHealth.checked_at).getTime()) > 2 * 60 * 1000
              ? <Tag color="default">Offline</Tag>
              : <Tag color={lastHealth.details?.is_busy ? "orange" : "green"}>
                  {lastHealth.details?.is_busy ? "Busy" : "Idle"}
                </Tag>
          )}
        </Space>
        <Button
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
          loading={loading}
        >
          Refresh
        </Button>
      </Space>

      {/* Stat cards */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }} align="middle" wrap={false}>
        <Col flex="none">
          <CircularBarplotAnimated size={80} label={name} />
        </Col>
        <Col flex="1">
          <Card size="small" styles={{ body: { padding: "8px 12px" } }}>
            <Statistic title="Tasks" value={totalTasks} prefix={<FileTextOutlined />} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col flex="1">
          <Card size="small" styles={{ body: { padding: "8px 12px" } }}>
            <Statistic title="Memories" value={totalMemories} prefix={<DatabaseOutlined />} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col flex="1">
          <Card size="small" styles={{ body: { padding: "8px 12px" } }}>
            <Statistic title="Research" value={metrics?.researchCount ?? 0} prefix={<FileTextOutlined />} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col flex="1">
          <Card size="small" styles={{ body: { padding: "8px 12px" } }}>
            <Statistic title="Convos" value={metrics?.conversationCount ?? 0} prefix={<MessageOutlined />} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col flex="1">
          <Card size="small" styles={{ body: { padding: "8px 12px" } }}>
            <Statistic title="Repos" value={metrics?.repoCount ?? 0} prefix={<CloudServerOutlined />} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col flex="1">
          <Card size="small" styles={{ body: { padding: "8px 12px" } }}>
            <Statistic
              title="Tokens (24h)"
              value={metrics?.tokenUsage?.total ?? 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ fontSize: 20 }}
              formatter={(v) => {
                const n = Number(v);
                if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
                if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
                return String(n);
              }}
            />
          </Card>
        </Col>
        <Col flex="1">
          <Card size="small" styles={{ body: { padding: "8px 12px" } }}>
            <Statistic
              title="Sys Prompt"
              value={metrics?.systemPromptTokens ?? 0}
              prefix={<SettingOutlined />}
              valueStyle={{ fontSize: 20 }}
              suffix="tokens"
              formatter={(v) => {
                const n = Number(v);
                if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
                if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
                return String(n);
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Tabs
        defaultActiveKey="overview"
        destroyOnHidden
        items={[
          {
            key: "overview",
            label: "Overview",
            children: <OverviewTab name={name} metrics={metrics} loading={loading} refreshKey={refreshKey} />,
          },
          {
            key: "chat",
            label: "Chat",
            children: <ChatTab name={name} refreshKey={refreshKey} />,
          },
          {
            key: "skills",
            label: `Skills (${skillCount})`,
            children: <SkillsTab name={name} refreshKey={refreshKey} onCountChange={setSkillCount} />,
          },
          {
            key: "repos",
            label: `Repos (${repoCount})`,
            children: <ReposTab name={name} refreshKey={refreshKey} onCountChange={setRepoCount} onMutate={fetchMetrics} />,
          },
          {
            key: "tasks",
            label: `Tasks (${tasks.length})`,
            children: <TasksTab name={name} tasks={tasks} tasksLoading={tasksLoading} onFiltersChange={handleTaskFiltersChange} refreshKey={refreshKey} />,
          },
          {
            key: "research",
            label: "Research",
            children: <ResearchTab name={name} refreshKey={refreshKey} />,
          },
          {
            key: "memories",
            label: "Memories",
            children: <MemoriesTab name={name} refreshKey={refreshKey} />,
          },
          {
            key: "memory-graph",
            label: "Memory Graph",
            children: <MemoryGraphTab name={name} refreshKey={refreshKey} />,
          },
          {
            key: "settings",
            label: <span><SettingOutlined /> Settings</span>,
            children: <SettingsTab name={name} refreshKey={refreshKey} />,
          },
        ]}
      />
    </div>
  );
}
