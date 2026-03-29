"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;

interface ConfigEntry {
  key: string;
  value: string;
  description: string | null;
  updated_at: string;
}

/** Group keys by prefix (e.g. "cron.task_check.enabled" → "cron") */
function getPrefix(key: string): string {
  const dot = key.indexOf(".");
  return dot > 0 ? key.substring(0, dot) : "general";
}

const PREFIX_COLORS: Record<string, string> = {
  cron: "purple",
  heartbeat: "blue",
  healthcheck: "cyan",
  channels: "green",
  memory: "orange",
  conversations: "gold",
  config_sync: "geekblue",
  general: "default",
};

export default function ConfigPage() {
  const [configs, setConfigs] = useState<ConfigEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ConfigEntry | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetchConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/config");
      const data = await res.json();
      setConfigs(Array.isArray(data) ? data : []);
    } catch {
      setConfigs([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchConfigs();
  }, [fetchConfigs]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (entry: ConfigEntry) => {
    setEditing(entry);
    form.setFieldsValue({
      key: entry.key,
      value: entry.value,
      description: entry.description || "",
    });
    setModalOpen(true);
  };

  const handleSave = async (values: { key: string; value: string; description?: string }) => {
    setSaving(true);
    try {
      const res = await fetch("/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Save failed");
      }
      message.success(editing ? "Config updated" : "Config added");
      setModalOpen(false);
      form.resetFields();
      setEditing(null);
      fetchConfigs();
    } catch (err: any) {
      message.error(err?.message || "Failed to save config");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (key: string) => {
    try {
      const res = await fetch("/api/config", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      if (!res.ok) throw new Error("Delete failed");
      message.success("Config deleted");
      fetchConfigs();
    } catch {
      message.error("Failed to delete config");
    }
  };

  const filtered = configs.filter((c) => {
    const q = search.toLowerCase();
    if (!q) return true;
    return c.key.toLowerCase().includes(q) || (c.description || "").toLowerCase().includes(q) || c.value.toLowerCase().includes(q);
  });

  const columns = [
    {
      title: "Key",
      dataIndex: "key",
      key: "key",
      width: 320,
      sorter: (a: ConfigEntry, b: ConfigEntry) => a.key.localeCompare(b.key),
      render: (key: string) => {
        const prefix = getPrefix(key);
        return (
          <Space>
            <Tag color={PREFIX_COLORS[prefix] || "default"}>{prefix}</Tag>
            <Text strong style={{ fontFamily: "monospace", fontSize: 13 }}>{key}</Text>
          </Space>
        );
      },
    },
    {
      title: "Value",
      dataIndex: "value",
      key: "value",
      ellipsis: true,
      render: (v: string) => (
        <Text style={{ fontFamily: "monospace", fontSize: 13 }}>{v}</Text>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      width: 280,
      render: (v: string | null) => v ? <Text type="secondary">{v}</Text> : null,
    },
    {
      title: "Updated",
      dataIndex: "updated_at",
      key: "updated_at",
      width: 160,
      sorter: (a: ConfigEntry, b: ConfigEntry) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      render: (v: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {new Date(v).toLocaleString()}
        </Text>
      ),
    },
    {
      title: "",
      key: "actions",
      width: 80,
      render: (_: unknown, record: ConfigEntry) => (
        <Space size={4}>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm
            title="Delete this config?"
            description={<Text type="secondary" style={{ fontSize: 12 }}>{record.key}</Text>}
            onConfirm={() => handleDelete(record.key)}
            okText="Delete"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Platform Config</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchConfigs} />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Add Config
          </Button>
        </Space>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder="Search by key, value, or description..."
          prefix={<SearchOutlined />}
          allowClear
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 320 }}
        />
        {search && (
          <Text type="secondary" style={{ marginLeft: 12 }}>
            {filtered.length} of {configs.length} entries
          </Text>
        )}
      </div>

      <Card size="small">
        <Table
          dataSource={filtered}
          columns={columns}
          rowKey="key"
          pagination={false}
          size="small"
          loading={loading}
        />
      </Card>

      <Modal
        title={editing ? "Edit Config" : "Add Config"}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditing(null); }}
        onOk={() => form.submit()}
        confirmLoading={saving}
        okText={editing ? "Update" : "Add"}
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleSave} style={{ marginTop: 16 }}>
          <Form.Item
            name="key"
            label="Key"
            rules={[{ required: true, message: "Key is required" }]}
          >
            <Input
              placeholder="e.g. heartbeat.interval_seconds"
              disabled={!!editing}
              style={{ fontFamily: "monospace" }}
            />
          </Form.Item>
          <Form.Item
            name="value"
            label="Value"
            rules={[{ required: true, message: "Value is required" }]}
          >
            <Input.TextArea
              rows={3}
              placeholder="Config value"
              style={{ fontFamily: "monospace", fontSize: 13 }}
            />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input placeholder="What this config controls" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
