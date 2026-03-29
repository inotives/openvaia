"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, Space, Table, Tag, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { AgentHealth } from "@/lib/types";

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

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<AgentHealth[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/dashboard/agents");
      const data = await res.json();
      if (!data.error) setAgents(data);
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const columns = [
    {
      title: "Agent",
      dataIndex: "name",
      key: "name",
      render: (name: string) => (
        <a onClick={() => router.push(`/agents/${name}`)}>{name}</a>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (v: string) => <Tag color={v === "online" ? "green" : "default"}>{v}</Tag>,
    },
    {
      title: "Healthy",
      dataIndex: "healthy",
      key: "healthy",
      render: (v: boolean | null) =>
        v === null ? <Tag>—</Tag> : v ? <Tag color="green">Yes</Tag> : <Tag color="red">No</Tag>,
    },
    {
      title: "Last Seen",
      dataIndex: "last_seen",
      key: "last_seen",
      render: timeAgo,
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
        <Title level={3} style={{ margin: 0 }}>Agents</Title>
        <Button icon={<ReloadOutlined />} onClick={fetchAgents} loading={loading}>
          Refresh
        </Button>
      </Space>
      <Card size="small">
        <Table
          dataSource={agents}
          columns={columns}
          rowKey="name"
          pagination={false}
          size="small"
          loading={loading}
          onRow={(record) => ({
            style: { cursor: "pointer" },
            onClick: () => router.push(`/agents/${record.name}`),
          })}
        />
      </Card>
    </div>
  );
}
