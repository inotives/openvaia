"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
  Popconfirm,
  message,
} from "antd";
import {
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { CronJob } from "@/lib/types";

const { Title, Text } = Typography;

export default function CronJobsPage() {
  const [jobs, setJobs] = useState<CronJob[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterAgent, setFilterAgent] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState<CronJob | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [form] = Form.useForm();

  const selectedRef = React.useRef<CronJob | null>(null);
  selectedRef.current = selected;

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/cron-jobs");
      const data = await res.json();
      if (!data.error) {
        setJobs(data);
        const cur = selectedRef.current;
        if (cur) {
          const updated = data.find((j: CronJob) => j.id === cur.id);
          if (updated) setSelected(updated);
        }
      }
    } catch (err) {
      console.error("Failed to fetch cron jobs:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch("/api/dashboard/agents");
      const data = await res.json();
      if (!data.error) setAgents(data.map((a: { name: string }) => a.name));
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    fetchAgents();
  }, [fetchJobs, fetchAgents]);

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({ interval_minutes: 30, enabled: true, agent_name: null });
    setCreateOpen(true);
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const res = await fetch("/api/cron-jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Create failed");
      }
      message.success("Cron job created");
      setCreateOpen(false);
      fetchJobs();
    } catch (err: any) {
      console.error("Save error:", err);
      message.error(err?.message || "Failed to save cron job");
    } finally {
      setSaving(false);
    }
  };

  const handleEditSave = async () => {
    if (!selected) return;
    const promptEl = document.getElementById("cron-prompt-edit") as HTMLTextAreaElement;
    const intervalEl = document.getElementById("cron-interval-edit") as HTMLInputElement;
    const enabledEl = document.getElementById("cron-enabled-edit") as HTMLInputElement;
    if (!promptEl) return;

    setEditSaving(true);
    try {
      const res = await fetch(`/api/cron-jobs/${selected.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: promptEl.value,
          interval_minutes: intervalEl ? parseInt(intervalEl.value, 10) || selected.interval_minutes : selected.interval_minutes,
          enabled: enabledEl ? enabledEl.checked : selected.enabled,
        }),
      });
      if (!res.ok) throw new Error("Update failed");
      message.success("Cron job updated");
      setEditOpen(false);
      fetchJobs();
    } catch (err: any) {
      console.error("Save error:", err);
      message.error(err?.message || "Failed to update cron job");
    } finally {
      setEditSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    const job = jobs.find((j) => j.id === id);
    try {
      const res = await fetch(`/api/cron-jobs/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Delete failed");
      if (job?.agent_name && job.last_run_at) {
        message.success(`Cron job deleted. Restart ${job.agent_name} to stop it immediately.`, 5);
      } else {
        message.success("Cron job deleted");
      }
      if (selected?.id === id) setSelected(null);
      fetchJobs();
    } catch (err) {
      console.error("Delete error:", err);
      message.error("Failed to delete cron job");
    }
  };

  const handleToggle = async (job: CronJob) => {
    try {
      const res = await fetch(`/api/cron-jobs/${job.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !job.enabled }),
      });
      if (!res.ok) throw new Error("Toggle failed");
      fetchJobs();
    } catch (err) {
      console.error("Toggle error:", err);
      message.error("Failed to toggle cron job");
    }
  };

  const formatInterval = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    if (minutes < 1440) {
      const h = Math.floor(minutes / 60);
      const m = minutes % 60;
      return m ? `${h}h ${m}m` : `${h}h`;
    }
    const d = Math.floor(minutes / 1440);
    const rem = minutes % 1440;
    const h = Math.floor(rem / 60);
    return h ? `${d}d ${h}h` : `${d}d`;
  };

  const columns = [
    {
      title: "Agent",
      dataIndex: "agent_name",
      key: "agent_name",
      width: 120,
      render: (v: string | null) => v ? <Tag>{v}</Tag> : <Tag color="blue">all agents</Tag>,
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      width: 200,
      render: (v: string, record: CronJob) => (
        <Space size={4}>
          <a onClick={(e) => { e.stopPropagation(); setSelected(record); }}>{v}</a>
          {!record.last_run_at && record.enabled && record.agent_name && (
            <Tooltip title="New cron job — restart the agent for it to take effect">
              <Popconfirm
                title={`Restart ${record.agent_name}?`}
                description="Agent will restart within 60 seconds to load new cron jobs."
                onConfirm={async (e) => {
                  e?.stopPropagation();
                  try {
                    const res = await fetch(`/api/agents/${record.agent_name}/restart`, { method: "POST" });
                    if (res.ok) message.success(`Restart requested for ${record.agent_name}`);
                    else message.error("Failed to request restart");
                  } catch { message.error("Failed to request restart"); }
                }}
                onCancel={(e) => e?.stopPropagation()}
                okText="Restart"
              >
                <WarningOutlined
                  style={{ color: "#faad14", fontSize: 14, cursor: "pointer" }}
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>
            </Tooltip>
          )}
          {!record.last_run_at && record.enabled && !record.agent_name && (
            <Tooltip title="New global cron job — restart agents for it to take effect">
              <WarningOutlined style={{ color: "#faad14", fontSize: 14 }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: "Prompt",
      dataIndex: "prompt",
      key: "prompt",
      ellipsis: true,
      render: (v: string) => (
        <Tooltip title={v} placement="topLeft">
          <span>{v}</span>
        </Tooltip>
      ),
    },
    {
      title: "Interval",
      dataIndex: "interval_minutes",
      key: "interval_minutes",
      width: 100,
      render: (v: number) => <Tag>{formatInterval(v)}</Tag>,
    },
    {
      title: "Enabled",
      dataIndex: "enabled",
      key: "enabled",
      width: 90,
      render: (_: boolean, record: CronJob) => (
        <Switch size="small" checked={record.enabled} onChange={(_, e) => { e.stopPropagation(); handleToggle(record); }} />
      ),
    },
    {
      title: "Last Run",
      dataIndex: "last_run_at",
      key: "last_run_at",
      width: 180,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString() : <Text type="secondary">never</Text>,
    },
    {
      title: "",
      key: "actions",
      width: 40,
      render: (_: unknown, record: CronJob) => (
        <Popconfirm
          title="Delete this cron job?"
          onConfirm={() => handleDelete(record.id)}
          okText="Delete"
          okButtonProps={{ danger: true }}
        >
          <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
        <Title level={3} style={{ margin: 0 }}>
          Cron Jobs
        </Title>
        <Space>
          <Button icon={<PlusOutlined />} type="primary" onClick={openCreate}>
            Add Job
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchJobs} loading={loading}>
            Refresh
          </Button>
        </Space>
      </Space>

      <div style={{ marginBottom: 16 }}>
        <Select
          placeholder="All agents"
          allowClear
          value={filterAgent}
          onChange={(v) => setFilterAgent(v || null)}
          style={{ width: 180 }}
          options={[
            { label: "Global only", value: "__global__" },
            ...agents.map((a) => ({ label: a, value: a })),
          ]}
        />
      </div>

      <Card size="small">
        <Table
          dataSource={filterAgent ? jobs.filter((j) => filterAgent === "__global__" ? !j.agent_name : j.agent_name === filterAgent) : jobs}
          columns={columns}
          rowKey="id"
          pagination={false}
          size="small"
          loading={loading}
          onRow={(record) => ({
            onClick: () => setSelected(record),
            style: { cursor: "pointer" },
          })}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="Add Cron Job"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        confirmLoading={saving}
        okText="Create"
        width={600}
        forceRender
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            label="Agent"
            name="agent_name"
            help="Leave empty for a global job (runs on all agents)"
          >
            <Select
              placeholder="All agents (global)"
              allowClear
              options={agents.map((a) => ({ label: a, value: a }))}
            />
          </Form.Item>
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: "Name is required" }]}
          >
            <Input placeholder="e.g. crypto_news" />
          </Form.Item>
          <Form.Item
            label="Prompt"
            name="prompt"
            rules={[{ required: true, message: "Prompt is required" }]}
          >
            <Input.TextArea rows={8} placeholder="The prompt sent to the agent on each run (supports markdown)" style={{ fontFamily: "monospace", fontSize: 13 }} />
          </Form.Item>
          <Form.Item label="Interval (minutes)" name="interval_minutes">
            <InputNumber min={1} max={14400} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="Enabled" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Drawer */}
      <Drawer
        title={selected?.name}
        open={!!selected}
        onClose={() => setSelected(null)}
        width={560}
        extra={
          selected && (
            <Button icon={<EditOutlined />} onClick={() => setEditOpen(true)}>
              Edit
            </Button>
          )
        }
      >
        {selected && (
          <div>
            {/* Header tags */}
            <Space style={{ marginBottom: 16 }}>
              {selected.agent_name
                ? <Tag>{selected.agent_name}</Tag>
                : <Tag color="blue">all agents</Tag>
              }
              <Tag color={selected.enabled ? "green" : "default"}>
                {selected.enabled ? "Enabled" : "Disabled"}
              </Tag>
              <Tag icon={<ClockCircleOutlined />}>
                {formatInterval(selected.interval_minutes)}
              </Tag>
            </Space>

            {/* Prompt content rendered as markdown */}
            <div style={{ marginBottom: 20 }}>
              <Text type="secondary" style={{ display: "block", marginBottom: 8 }}>Prompt</Text>
              <Card
                size="small"
                style={{ maxHeight: 400, overflow: "auto" }}
                styles={{ body: { padding: 16 } }}
              >
                <div style={{ whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 13 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{selected.prompt}</ReactMarkdown>
                </div>
              </Card>
            </div>

            {/* Metadata */}
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">Interval: </Text>
              <Text>{selected.interval_minutes} minutes ({formatInterval(selected.interval_minutes)})</Text>
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">Last Run: </Text>
              <Text>{selected.last_run_at ? new Date(selected.last_run_at).toLocaleString() : "Never"}</Text>
            </div>
            {selected.enabled && (
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">Next Run: </Text>
                <Text>
                  {(() => {
                    const base = selected.last_run_at ? new Date(selected.last_run_at) : new Date(selected.created_at);
                    const next = new Date(base.getTime() + selected.interval_minutes * 60000);
                    const now = Date.now();
                    if (next.getTime() <= now) return "Due now";
                    const diffMin = Math.round((next.getTime() - now) / 60000);
                    const label = diffMin < 60 ? `${diffMin}m` : diffMin < 1440 ? `${Math.floor(diffMin / 60)}h ${diffMin % 60}m` : `${Math.floor(diffMin / 1440)}d`;
                    return `${next.toLocaleString()} (in ${label})`;
                  })()}
                </Text>
              </div>
            )}
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">Created: </Text>
              <Text>{new Date(selected.created_at).toLocaleString()}</Text>
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">Updated: </Text>
              <Text>{new Date(selected.updated_at).toLocaleString()}</Text>
            </div>

            {/* Delete */}
            <div style={{ marginTop: 24, borderTop: "1px solid #f0f0f0", paddingTop: 16 }}>
              <Popconfirm
                title="Delete this cron job?"
                description="This action cannot be undone."
                onConfirm={() => handleDelete(selected.id)}
                okText="Delete"
                okButtonProps={{ danger: true }}
              >
                <Button danger icon={<DeleteOutlined />}>
                  Delete Cron Job
                </Button>
              </Popconfirm>
            </div>
          </div>
        )}
      </Drawer>

      {/* Edit Modal (like skills edit) */}
      <Modal
        title={selected?.name}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        width={700}
        footer={[
          <Button key="cancel" onClick={() => setEditOpen(false)}>Cancel</Button>,
          <Button key="save" type="primary" loading={editSaving} onClick={handleEditSave}>Save</Button>,
        ]}
      >
        {selected && (
          <div style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>Prompt (Markdown)</Text>
              <Input.TextArea
                id="cron-prompt-edit"
                defaultValue={selected.prompt}
                key={`prompt-${selected.id}-${editOpen}`}
                rows={16}
                style={{ fontFamily: "monospace", fontSize: 13 }}
              />
            </div>
            <Space size="large">
              <div>
                <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>Interval (minutes)</Text>
                <Input
                  id="cron-interval-edit"
                  type="number"
                  defaultValue={selected.interval_minutes}
                  key={`interval-${selected.id}-${editOpen}`}
                  style={{ width: 120 }}
                  min={1}
                  max={14400}
                />
              </div>
              <div>
                <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>Enabled</Text>
                <input
                  id="cron-enabled-edit"
                  type="checkbox"
                  defaultChecked={selected.enabled}
                  key={`enabled-${selected.id}-${editOpen}`}
                  style={{ width: 18, height: 18 }}
                />
              </div>
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
}
