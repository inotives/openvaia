"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button, Card, Col, Row, Space, Table, Tag, Typography } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import type { AgentHealth, TaskSummaryRow } from "@/lib/types";
import { STATUS_COLORS, STATUS_LABELS, STATUSES } from "@/lib/constants";

interface SchedulerTask {
  name: string;
  type: "heartbeat" | "cron";
  interval: string;
  enabled: boolean;
  description: string;
}

interface SchedulerInfo {
  agent: string;
  status: string;
  is_busy: boolean;
  uptime_seconds: number;
  last_heartbeat: string | null;
  tasks: SchedulerTask[];
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  if (hrs < 24) return `${hrs}h ${remainMins}m`;
  const days = Math.floor(hrs / 24);
  return `${days}d ${hrs % 24}h`;
}

const { Title } = Typography;

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "—";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function DashboardPage() {
  const [agents, setAgents] = useState<AgentHealth[]>([]);
  const [tasks, setTasks] = useState<TaskSummaryRow[]>([]);
  const [scheduler, setScheduler] = useState<SchedulerInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [a, t, s] = await Promise.all([
        fetch("/api/dashboard/agents").then((r) => r.json()),
        fetch("/api/dashboard/tasks").then((r) => r.json()),
        fetch("/api/dashboard/scheduler").then((r) => r.json()),
      ]);
      if (!a.error) setAgents(a);
      if (!t.error) setTasks(t);
      if (!s.error) setScheduler(s);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const agentColumns = [
    {
      title: "Agent",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: any) => (
        <span>{name}{record.role ? <span style={{ color: "#8c8c8c", marginLeft: 6 }}>({record.role})</span> : null}</span>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (v: string) => (
        <Tag color={v === "online" ? "green" : "default"}>{v}</Tag>
      ),
    },
    {
      title: "Healthy",
      dataIndex: "healthy",
      key: "healthy",
      render: (v: boolean | null) =>
        v === null ? <Tag>—</Tag> : v ? <Tag color="green">Yes</Tag> : <Tag color="red">No</Tag>,
    },
    {
      title: "Skills",
      dataIndex: "skill_count",
      key: "skills",
      render: (v: number) => v || 0,
    },
    {
      title: "Last Seen",
      dataIndex: "last_seen",
      key: "last_seen",
      render: timeAgo,
    },
  ];

  const taskColumns = [
    { title: "Agent", dataIndex: "agent", key: "agent" },
    ...STATUSES.map((s) => ({
      title: STATUS_LABELS[s],
      dataIndex: s,
      key: s,
      render: (v: number) =>
        v > 0 ? <Tag color={STATUS_COLORS[s]}>{v}</Tag> : <span style={{ color: "#ccc" }}>0</span>,
    })),
  ];

  const schedulerColumns = [
    { title: "Agent", dataIndex: "agent", key: "agent" },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (v: string) => (
        <Tag color={v === "online" ? "green" : "default"}>{v}</Tag>
      ),
    },
    {
      title: "Busy",
      dataIndex: "is_busy",
      key: "busy",
      render: (v: boolean) =>
        v ? <Tag color="orange">Yes</Tag> : <Tag color="default">No</Tag>,
    },
    {
      title: "Uptime",
      dataIndex: "uptime_seconds",
      key: "uptime",
      render: (v: number) => formatUptime(v),
    },
    {
      title: "Last Heartbeat",
      dataIndex: "last_heartbeat",
      key: "heartbeat",
      render: timeAgo,
    },
  ];

  const taskDetailColumns = [
    { title: "Task", dataIndex: "name", key: "name" },
    {
      title: "Type",
      dataIndex: "type",
      key: "type",
      render: (v: string) => (
        <Tag color={v === "heartbeat" ? "blue" : "purple"}>{v}</Tag>
      ),
    },
    { title: "Interval", dataIndex: "interval", key: "interval" },
    {
      title: "Enabled",
      dataIndex: "enabled",
      key: "enabled",
      render: (v: boolean) =>
        v ? (
          <CheckCircleOutlined style={{ color: "#52c41a" }} />
        ) : (
          <CloseCircleOutlined style={{ color: "#ff4d4f" }} />
        ),
    },
    { title: "Description", dataIndex: "description", key: "description" },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
        <Title level={3} style={{ margin: 0 }}>
          Dashboard
        </Title>
        <Button icon={<ReloadOutlined />} onClick={fetchAll} loading={loading}>
          Refresh
        </Button>
      </Space>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="Agent Status" size="small">
            <Table
              dataSource={agents}
              columns={agentColumns}
              rowKey="name"
              pagination={false}
              size="small"
              loading={loading}
            />
          </Card>
        </Col>

        <Col span={24}>
          <Card title="Agent Scheduler" size="small">
            <Table
              dataSource={scheduler}
              columns={schedulerColumns}
              rowKey="agent"
              pagination={false}
              size="small"
              loading={loading}
              expandable={{
                expandedRowRender: (record: SchedulerInfo) => (
                  <Table
                    dataSource={record.tasks}
                    columns={taskDetailColumns}
                    rowKey="name"
                    pagination={false}
                    size="small"
                  />
                ),
              }}
            />
          </Card>
        </Col>

        <Col span={24}>
          <Card title="Task Summary" size="small">
            <Table
              dataSource={tasks}
              columns={taskColumns}
              rowKey="agent"
              pagination={false}
              size="small"
              loading={loading}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
